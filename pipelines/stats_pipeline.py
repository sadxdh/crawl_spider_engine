"""
统计 Pipeline
Priority: 200
"""
import time
from loguru import logger
from utils.redis_client import get_redis
from config import STATS_KEY


class StatsPipeline:
    """记录 item 处理统计，close_spider 时推送到 Redis"""

    def __init__(self):
        self.item_count = 0
        self.start_time = None

    def open_spider(self, spider):
        self.start_time = time.time()
        logger.info(f"[StatsPipeline] 开始: {spider.name}")

    def process_item(self, item, spider):
        self.item_count += 1
        return item

    def close_spider(self, spider):
        elapsed = time.time() - self.start_time
        scrapy_stats = spider.crawler.stats.get_stats()

        dedup_batch = int(scrapy_stats.get('pipeline/dedup_batch', 0))
        dedup_db    = int(scrapy_stats.get('pipeline/dedup_db', 0))
        inserted    = int(scrapy_stats.get('pipeline/mysql_inserted', self.item_count))
        updated     = int(scrapy_stats.get('pipeline/mysql_updated', 0))
        failed      = int(scrapy_stats.get('pipeline/mysql_failed', 0))
        total_scraped = self.item_count + dedup_batch + dedup_db

        logger.info(
            f"[StatsPipeline] 结束: {spider.name} | "
            f"总采集={total_scraped} 入库={self.item_count} "
            f"新增={inserted} 更新={updated} 失败={failed} "
            f"批次重复={dedup_batch} 库内重复={dedup_db} 耗时={elapsed:.1f}s"
        )

        # 推送到 Redis，供监控平台读取
        try:
            r = get_redis()
            key = STATS_KEY.format(spider.name)
            r.hset(key, mapping={
                'item_scraped_count':   str(self.item_count),
                'mysql_inserted_count': str(inserted),
                'mysql_updated_count':  str(updated),
                'mysql_failed_count':   str(failed),
                'item_total_count':     str(total_scraped),
                'dedup_batch_count':    str(dedup_batch),
                'dedup_db_count':       str(dedup_db),
                'elapsed_seconds':      str(round(elapsed, 1)),
                'downloader/request_count':
                    str(scrapy_stats.get('downloader/request_count', 0)),
                'downloader/response_received_count':
                    str(scrapy_stats.get('downloader/response_received_count', 0)),
                'downloader/exception_count':
                    str(scrapy_stats.get('downloader/exception_count', 0)),
                'dupefilter/filtered':
                    str(scrapy_stats.get('dupefilter/filtered', 0)),
            })
            r.expire(key, 3600)
        except Exception as e:
            logger.warning(f"[StatsPipeline] Redis 推送失败: {e}")
