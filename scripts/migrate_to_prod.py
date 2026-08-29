"""管理数据迁移：测试库 → 生产库
用法: python migrate_to_prod.py
生产库连接从环境变量自动读取，无需参数
"""
import os, pymysql

SOURCE_HOST = 'py.w.com'
SOURCE_USER = 'root'
SOURCE_PASS = 'IK29lKb0'

TARGET_HOST = os.environ.get('SPIDER_MYSQL_HOST_PROD', '')
TARGET_USER = os.environ.get('SPIDER_MYSQL_USER_PROD', 'root')
TARGET_PASS = os.environ.get('SPIDER_MYSQL_PASSWORD_PROD', '')

CORE_TABLES = [
    'spider_group', 'spider_registry', 'spider_config',
    'spider_job', 'job_category', 'schedule_task',
    'account_pool', 'cookie_pool', 'sys_config', 'sys_user',
    'business', 'website',
]

OPTIONAL_TABLES = ['schedule_log', 'sync_log', 'alert_rule']


def migrate_table(src_conn, dst_conn, table, where='', limit=0):
    src_cur = src_conn.cursor()
    dst_cur = dst_conn.cursor()
    src_cur.execute(f'SELECT * FROM {table} LIMIT 0')
    cols = [d[0] for d in src_cur.description]
    col_names = ', '.join(cols)
    placeholders = ', '.join(['%s'] * len(cols))

    sql = f'SELECT * FROM {table}'
    if where:
        sql += f' WHERE {where}'
    if limit:
        sql += f' LIMIT {limit}'

    src_cur.execute(sql)
    rows = src_cur.fetchall()
    inserted = 0
    for row in rows:
        try:
            dst_cur.execute(
                f'INSERT IGNORE INTO {table} ({col_names}) VALUES ({placeholders})',
                row)
            if dst_cur.rowcount > 0:
                inserted += 1
        except Exception:
            pass

    dst_conn.commit()
    return inserted, len(rows)


def main():
    if not TARGET_HOST:
        print('错误: 环境变量 SPIDER_MYSQL_HOST_PROD 未设置')
        return

    print(f'迁移目标: {TARGET_HOST}')
    src = pymysql.connect(host=SOURCE_HOST, user=SOURCE_USER, password=SOURCE_PASS,
                          database='crawl_admin', charset='utf8mb4')
    dst = pymysql.connect(host=TARGET_HOST, user=TARGET_USER, password=TARGET_PASS,
                          database='crawl_admin', charset='utf8mb4')

    total_inserted = 0
    for table in CORE_TABLES:
        ins, total = migrate_table(src, dst, table)
        total_inserted += ins
        print(f'  {table:30s} {ins:>5}/{total:<5} rows')

    for table in OPTIONAL_TABLES:
        ins, total = migrate_table(src, dst, table, limit=5000)
        total_inserted += ins
        print(f'  {table:30s} {ins:>5}/{total:<5} rows (最近5000)')

    src.close()
    dst.close()
    print(f'\n迁移完成: {total_inserted} 行')


if __name__ == '__main__':
    main()
