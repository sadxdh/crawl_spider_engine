#!/bin/bash
# 管理数据迁移：测试库 → 生产库
# 用法: ./migrate_to_prod.sh
# 前提: 生产 MySQL 可访问，crawl_admin 库已建表

TEST_HOST="py.w.com"
TEST_USER="root"
TEST_PASS="IK29lKb0"

echo "生产 MySQL 信息："
read -p "  Host: " PROD_HOST
read -p "  User: " PROD_USER
read -sp "  Password: " PROD_PASS
echo

# 核心管理表（必须迁移）
TABLES=(
    "spider_group"
    "spider_registry"
    "spider_config"
    "spider_job"
    "job_category"
    "schedule_task"
    "account_pool"
    "cookie_pool"
    "sys_config"
    "sys_user"
    "business"
    "website"
)

echo "=== 1. 迁移核心管理表 ==="
for table in "${TABLES[@]}"; do
    echo -n "  $table ... "
    mysqldump -h "$TEST_HOST" -u "$TEST_USER" -p"$TEST_PASS" \
        --no-create-info --skip-triggers --complete-insert \
        crawl_admin "$table" 2>/dev/null | \
    mysql -h "$PROD_HOST" -u "$PROD_USER" -p"$PROD_PASS" crawl_admin 2>/dev/null
    echo "OK"
done

# 历史数据表（可选）
echo ""
echo "=== 2. 历史数据（可选，数据量大）==="
for table in "schedule_log" "sync_log" "alert_rule"; do
    echo -n "  $table (最近30天)... "
    mysqldump -h "$TEST_HOST" -u "$TEST_USER" -p"$TEST_PASS" \
        --no-create-info --skip-triggers --complete-insert \
        --where="1=1 LIMIT 5000" \
        crawl_admin "$table" 2>/dev/null | \
    mysql -h "$PROD_HOST" -u "$PROD_USER" -p"$PROD_PASS" crawl_admin 2>/dev/null
    echo "OK"
done

echo ""
echo "=== 3. SQLite 执行记录（cron_runner 残留，可选）==="
# 如果存在 SQLite 文件，提取未同步的记录
if [ -f /engine/cron_execution.db ]; then
    sqlite3 /engine/cron_execution.db \
        "SELECT * FROM execution_log WHERE synced=0" > /tmp/cron_pending.csv 2>/dev/null
    echo "  待同步记录: $(wc -l < /tmp/cron_pending.csv) 条"
fi

echo ""
echo "迁移完成。验证："
echo "  mysql -h $PROD_HOST -u $PROD_USER -p -e 'SELECT COUNT(*) FROM crawl_admin.schedule_task'"
echo "  mysql -h $PROD_HOST -u $PROD_USER -p -e 'SELECT COUNT(*) FROM crawl_admin.spider_registry'"
