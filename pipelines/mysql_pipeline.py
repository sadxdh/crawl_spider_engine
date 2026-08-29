"""
MySQL 入库 Pipeline (Priority=310)
表名优先使用 spider.data_table（来自 spider arg），其次 spider.name
"""
import json
from datetime import datetime
from loguru import logger
from scrapy.exceptions import DropItem
from utils.mysql_pool import get_mysql
from utils.dingtalk import send_dd_msg


class MysqlPipeline:
    """MySQL 数据入库，支持自动建表"""

    def __init__(self):
        self.item_count = 0
        self.error_count = 0
        self.updated_count = 0
        self.table_name = None
        self.create_table_rule = 'common'
        self._crawl_time_cache: dict[str, bool] = {}  # table -> has crawl_time col
        self._table_cols_cache: dict[str, set] = {}   # table -> {col names}
    def open_spider(self, spider):
        self.table_name = getattr(spider, 'data_table', spider.name)
        self.create_table_rule = getattr(spider, 'create_table_rule', 'common')
        dedup_fields = getattr(spider, 'dedup_fields', None) or []
        # 未声明时优先尝试 md5_value，其次 keyno
        if not dedup_fields:
            dedup_fields = ['md5_value', 'keyno']
        self._dedup_field = dedup_fields[0]
        logger.info(f"[MysqlPipeline] {spider.name} -> 表: {self.table_name} dedup={self._dedup_field}")

    def process_item(self, item, spider):
        if item is None:
            return None
        item_dict = dict(item)
        table = item_dict.pop('_table', None) or self.table_name
        item_dict.pop('spider_name', None)
        item_dict.pop('crawl_time', None)
        job_id = getattr(spider, 'jobid', 0)
        if job_id and not item_dict.get('jobid') and self._table_has_column(table, 'jobid'):
            item_dict['jobid'] = job_id
        try:
            updated = self._do_insert(table, item_dict, self._dedup_field)
            if updated:
                self.updated_count += 1
            else:
                self.item_count += 1
            return item
        except Exception as e:
            self.error_count += 1
            logger.error(f"[MysqlPipeline] 入库失败: {e} | {str(item_dict)[:80]}")
            raise DropItem(f"入库失败: {e}")

    def _table_has_column(self, table: str, column: str) -> bool:
        """检查表中是否存在指定列（带缓存）"""
        if table not in self._table_cols_cache:
            try:
                conn = get_mysql()
                with conn.cursor() as cur:
                    cur.execute(f'SHOW COLUMNS FROM `{table}`')
                    self._table_cols_cache[table] = {r['Field'] for r in cur.fetchall()}
                conn.close()
            except Exception:
                self._table_cols_cache[table] = set()
        return column in self._table_cols_cache.get(table, set())

    def _do_insert(self, table: str, item: dict, dedup_field: str = 'keyno', retries=3) -> bool:
        """入库：有 dedup 值→先查后写（存在 UPDATE / 不存在 INSERT），无 dedup 值→直接 INSERT
        返回 True=更新了已有记录, False=新插入
        """
        import time
        fields = list(item.keys())
        col_names = ', '.join([f'`{f}`' for f in fields])
        placeholders = ', '.join(['%s'] * len(fields))
        # values = [
        #     json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
        #     for v in item.values()
        # ]
        import datetime
        def _handle_value(value):
            if isinstance(value, str):
                value = value.strip()
            elif isinstance(value, bool):
                value = int(value)
            elif isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
                value = str(value)
            return value
        values = [
            json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else _handle_value(v)
            for v in item.values()
        ]
        dedup_val = item.get(dedup_field) if dedup_field else None

        if not dedup_val or not self._table_has_column(table, dedup_field):
            if dedup_val:
                logger.debug(f'[MysqlPipeline] 去重列 {dedup_field} 不在表 {table} 中，直接 INSERT')
            sql = f"INSERT INTO `{table}` ({col_names}) VALUES ({placeholders})"
            for attempt in range(1, retries + 1):
                conn = get_mysql()
                try:
                    with conn.cursor() as cur:
                        cur.execute(sql, values)
                    conn.commit()
                    return False
                except Exception as e:
                    if attempt < retries:
                        logger.warning(f'[MysqlPipeline] INSERT 重试 {attempt}/{retries}: {e}')
                        time.sleep(1)
                    else:
                        raise
                finally:
                    conn.close()
            return False

        # SELECT 查 id → UPDATE 或 INSERT
        for attempt in range(1, retries + 1):
            conn = get_mysql()
            try:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT id FROM `{table}` WHERE `{dedup_field}`=%s LIMIT 1", (dedup_val,))
                    row = cur.fetchone()
                # if row:
                #     existing_id = row['id']
                #     sets = ', '.join([f'`{f}`=%s' for f in fields if f not in ('id', 'created_time')])
                #     update_vals = [values[fields.index(f)] for f in fields if f not in ('id', 'created_time')]
                #     if sets:
                #         with conn.cursor() as cur:
                #             cur.execute(f"UPDATE `{table}` SET {sets} WHERE id=%s", update_vals + [existing_id])
                #     conn.commit()
                #     logger.info(f'[MysqlPipeline] UPDATE {table} id={existing_id} {dedup_field}={dedup_val}')
                #     return True
                logger.info(f'[MysqlPipeline] {item}')
                if row:
                    existing_id = row['id']
                    sets = ', '.join([f'`{f}`=%s' for f in fields if f not in ('id', 'created_time')])
                    update_vals = [values[fields.index(f)] for f in fields if f not in ('id', 'created_time')]
                    result = 0
                    if sets:
                        with conn.cursor() as cur:
                            cur.execute(f"UPDATE `{table}` SET {sets} WHERE id=%s", update_vals + [existing_id])
                            result = cur.rowcount
                    conn.commit()
                    if result == 1:
                        logger.info(f'[MysqlPipeline] UPDATE {table} id={existing_id} {dedup_field}={dedup_val}')
                    else:
                        logger.info(f'[MysqlPipeline] NOthing Changes {table} id={existing_id} {dedup_field}={dedup_val}')
                    return True
                else:
                    sql = f"INSERT INTO `{table}` ({col_names}) VALUES ({placeholders})"
                    with conn.cursor() as cur:
                        cur.execute(sql, values)
                    conn.commit()
                    logger.info(f'[MysqlPipeline] INSERT {table} {dedup_field}={dedup_val}')
                    return False
            except Exception as e:
                if attempt < retries:
                    logger.warning(f'[MysqlPipeline] Upsert 重试 {attempt}/{retries}: {e}')
                    time.sleep(1)
                else:
                    raise
            finally:
                conn.close()
        return False

    def close_spider(self, spider):
        dev = getattr(spider, 'developer', '')
        total = self.item_count + self.updated_count
        # 暴露给 Scrapy stats、日志解析和管理平台快照。
        spider.crawler.stats.set_value('pipeline/mysql_inserted', self.item_count)
        spider.crawler.stats.set_value('pipeline/mysql_updated', self.updated_count)
        spider.crawler.stats.set_value('pipeline/mysql_failed', self.error_count)
        # 回写 ScheduleLog 实际入库量
        if total > 0:
            try:
                import os, pymysql
                from config import DB_CONF
                scrapyd_job_id = os.environ.get('SCRAPY_JOB', '')
                conn = pymysql.connect(**DB_CONF)
                with conn.cursor() as cur:
                    if scrapyd_job_id:
                        cur.execute(
                            "UPDATE schedule_log SET items_count=%s WHERE scrapyd_job_id=%s",
                            (total, scrapyd_job_id))
                    if not scrapyd_job_id or cur.rowcount == 0:
                        cur.execute(
                            "UPDATE schedule_log SET items_count=%s WHERE spider_name=%s ORDER BY id DESC LIMIT 1",
                            (total, spider.name))
                conn.commit()
                conn.close()
                logger.info(f"[MysqlPipeline] 已回写 items_count={total} job={scrapyd_job_id}")
            except Exception as e:
                logger.debug(f"[MysqlPipeline] 回写失败: {e}")
        if self.error_count > 0:
            send_dd_msg(
                spider_name=spider.name,
                msg_name='入库异常',
                msg_content=f"本次: 新入库 {self.item_count}, 更新 {self.updated_count}, 失败 {self.error_count}",
                developer=dev,
            )
        logger.info(f"[MysqlPipeline] {spider.name} 结束: 新入库={self.item_count} 更新={self.updated_count} 失败={self.error_count} 表={self.table_name} dedup={getattr(self, '_dedup_field', '-')}")
