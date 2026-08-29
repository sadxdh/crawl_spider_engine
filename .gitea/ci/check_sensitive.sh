#!/bin/bash
# 敏感文件变更检测 — 非维护者修改禁止文件时直接驳回
# Gitea 配置: Settings → Webhooks → Gitea Actions，在 workflow 中调用此脚本

set -e

# 维护者（Gitea 用户名）
MAINTAINERS="${MAINTAINERS:-chenz}"

# 禁止修改的文件/目录
BLOCKED_PATHS=(
    "settings.py"
    "config/prod.ini"
    "config/docker.ini"
    "Dockerfile"
    "entrypoint.sh"
    "setup.py"
    "scrapy.cfg"
    "requirements.txt"
    ".gitattributes"
    ".gitea/"
    "scripts/"
    "docs/"
)

PUSHER="${GITEA_PUSHER_NAME:-$(git log -1 --format='%an')}"

is_maintainer() {
    for m in $MAINTAINERS; do
        [ "$PUSHER" = "$m" ] && return 0
    done
    return 1
}

CHANGED_FILES=$(git diff --name-only HEAD~1..HEAD 2>/dev/null || git diff --name-only HEAD)

echo "=== 敏感文件校验 ==="
echo "Pusher: $PUSHER"
echo "Changed files:"
echo "$CHANGED_FILES"
echo ""

BLOCKED=()
for file in $CHANGED_FILES; do
    for path in "${BLOCKED_PATHS[@]}"; do
        if [[ "$file" == "$path" || "$file" == "$path"* ]]; then
            BLOCKED+=("$file")
            break
        fi
    done
done

# 自保护：CI 脚本本身不允许非维护者修改，防止绕过
SELF_GUARD=(
    ".gitea/"
)
for file in $CHANGED_FILES; do
    for path in "${SELF_GUARD[@]}"; do
        if [[ "$file" == "$path"* ]]; then
            if ! is_maintainer; then
                echo "[REJECTED] $PUSHER 修改了 CI 保护文件: $file"
                echo ".gitea/ 目录仅限 chenz 修改。"
                exit 1
            fi
        fi
    done
done

if [ ${#BLOCKED[@]} -eq 0 ]; then
    echo "[PASS] 仅修改了爬虫脚本，校验通过"
    exit 0
fi

if is_maintainer; then
    echo "[OK] $PUSHER 是维护者，允许修改: ${BLOCKED[*]}"
    exit 0
fi

echo "[REJECTED] $PUSHER 修改了禁止文件: ${BLOCKED[*]}"
echo "这些文件影响线上运行，请联系 chenz。"
exit 1
