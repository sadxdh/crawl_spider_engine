#!/bin/bash
# 爬虫引擎部署脚本
# 用法: ./scripts/deploy.sh [version_tag]

set -e
cd "$(dirname "$0")/.."

VERSION="${1:-$(date +%Y%m%d%H%M%S)}"
SCRAPYD_URL="${SCRAPYD_URL:-http://localhost:6800}"
PROJECT="crawl_spider_engine"
EGG_FILE="dist/${PROJECT}-1.0-py3.12.egg"

echo "=== 爬虫引擎部署 ==="
echo "版本: $VERSION"
echo "目标: $SCRAPYD_URL"
echo ""

# 1. 构建 Egg
echo "[1/3] 构建 Egg..."
python setup.py bdist_egg 2>&1 | tail -1
if [ ! -f "$EGG_FILE" ]; then
    echo "ERROR: Egg 构建失败"
    exit 1
fi
echo "  OK: $EGG_FILE"

# 2. 上传到 Scrapyd
echo "[2/3] 部署到 Scrapyd..."
RESP=$(curl -s -X POST "${SCRAPYD_URL}/addversion.json" \
    -F "project=${PROJECT}" \
    -F "version=${VERSION}" \
    -F "egg=@${EGG_FILE}")
echo "  Response: $RESP"

# 3. 验证
echo "[3/3] 验证部署..."
SPIDERS=$(curl -s "${SCRAPYD_URL}/listspiders.json?project=${PROJECT}" | python -c "import json,sys; print(len(json.load(sys.stdin).get('spiders',[])))" 2>/dev/null || echo "?")
echo "  爬虫数量: $SPIDERS"
echo ""
echo "部署完成! 版本: $VERSION"
