#!/bin/bash
# Scrapyd 启动 + 自动部署 egg
set -e

echo "[entrypoint] 启动 Scrapyd..."
scrapyd --pidfile= &
SCRAPYD_PID=$!

# 等待就绪
for i in $(seq 1 30); do
    if curl -sf http://localhost:6800/daemonstatus.json > /dev/null 2>&1; then
        echo "[entrypoint] Scrapyd 已就绪"
        break
    fi
    sleep 1
done

# 始终从当前代码重新打包 egg（确保最新 spider 生效）
echo "[entrypoint] 构建 Egg..."
cd /app
rm -rf build dist *.egg-info
python setup.py bdist_egg
EGG=$(ls -t dist/*.egg 2>/dev/null | head -1)
if [ -n "$EGG" ]; then
    curl -s http://localhost:6800/addversion.json \
        -F project=crawl_spider_engine \
        -F version=$(date +%Y%m%d%H%M) \
        -F egg=@$EGG
    echo "[entrypoint] Egg 部署完成"
else
    echo "[entrypoint] Egg 构建失败"
fi

# Git 自检测热部署：代码目录挂载（/engine 或 ENGINE_DIR 指定）且有 .git 时启用。
# 宿主机 git pull → auto_deploy 检测到新 commit → egg 热部署（addversion.json），容器不重启。
# 生产若以挂载卷部署则此机制生效；未挂载时回退 webhook 重建容器。
ENGINE_DIR="${ENGINE_DIR:-/app}"
AUTO_DEPLOY_PID=""
if [ -d "${ENGINE_DIR}/.git" ] && command -v git > /dev/null 2>&1; then
    echo "[entrypoint] 启动 Git 自检测（间隔 30s, dir=${ENGINE_DIR}）..."
    ENGINE_DIR="${ENGINE_DIR}" python /app/scripts/auto_deploy.py &
    AUTO_DEPLOY_PID=$!
else
    echo "[entrypoint] 未挂载 Git 元数据（${ENGINE_DIR}/.git 不存在），跳过自检测（由 webhook 重建部署）"
fi

# 凭证接口连通性检测
echo "[entrypoint] 检测凭证接口..."
ADMIN_URL="${ADMIN_API_URL:-http://10.88.0.1:5000}"
for i in $(seq 1 10); do
    if curl -sf "${ADMIN_URL}/health" > /dev/null 2>&1; then
        echo "[entrypoint] 凭证接口就绪: ${ADMIN_URL}"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "[entrypoint] 凭证接口不可达: ${ADMIN_URL} (spider仍可运行,凭证功能不可用)"
    fi
    sleep 3
done

# 启动代理可用性检测
echo "[entrypoint] 启动代理检测（间隔 5min）..."
python /app/scripts/proxy_checker.py &
PROXY_CHECKER_PID=$!

echo "[entrypoint] 就绪 (Scrapyd=$SCRAPYD_PID, AutoDeploy=${AUTO_DEPLOY_PID:-disabled}, ProxyCheck=$PROXY_CHECKER_PID)"
wait $SCRAPYD_PID
