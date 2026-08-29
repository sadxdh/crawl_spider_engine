#!/bin/bash
# Docker 环境启动脚本
# 启动顺序: scrapyd → backend → frontend → cron_runner → node_service

set -e
COMPOSE_DIR="$(dirname "$0")/../../crawl_admin_server/docker"

echo "=== 启动爬虫平台 Docker 环境 ==="

# 1. 启动核心服务
echo "[1/4] 启动 Scrapyd + Backend + Frontend..."
cd "$COMPOSE_DIR"
docker compose up -d scrapyd backend frontend 2>&1 | tail -3

# 2. 等待 Scrapyd 就绪
echo "[2/4] 等待 Scrapyd..."
for i in $(seq 1 30); do
    if curl -s http://localhost:6800/daemonstatus.json > /dev/null 2>&1; then
        echo "  Scrapyd 就绪"
        break
    fi
    sleep 2
done

# 3. 启动辅助服务
echo "[3/4] 启动 cron_runner + node_service..."
docker compose up -d cron_runner node_service 2>&1 | tail -3

# 4. 部署最新代码
echo "[4/4] 部署爬虫代码..."
cd "$(dirname "$0")/.."
python setup.py bdist_egg 2>&1 | tail -1
VER="startup$(date +%H%M%S)"
curl -s -X POST http://localhost:6800/addversion.json \
    -F "project=crawl_spider_engine" -F "version=${VER}" \
    -F "egg=@dist/crawl_spider_engine-1.0-py3.12.egg" > /dev/null
echo "  部署完成: ${VER}"

echo ""
echo "=== 平台已启动 ==="
echo "  Scrapyd:      http://localhost:6800"
echo "  Backend API:  http://localhost:5000"
echo "  Frontend:     http://localhost:3000"
echo "  Universal:    http://localhost:8100"
echo "  Node Service: http://localhost:3001"
echo "  Cron Runner:  http://localhost:6801"
