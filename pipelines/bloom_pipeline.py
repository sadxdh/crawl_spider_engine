"""
布隆过滤器去重 Pipeline (Priority=100)
Key: crawl_engine:dupefilter:req:{spider.name}
bloom_reset 由 spider.bloom_reset 控制（来自 spider arg）
"""
from scrapy.exceptions import DropItem
from utils.bloom_filter import get_bloom_filter
from utils.redis_client import get_redis
from loguru import logger


class BloomFilterPipeline:
    """布隆过滤器去重，防止重复入库"""

    def open_spider(self, spider):
        self._redis = get_redis()
        self.bloom = get_bloom_filter(self._redis, spider.name)

        # bloom_reset 由 spider arg 控制
        if getattr(spider, 'bloom_reset', False):
            self.bloom.reset()
            logger.info(f"[BloomPipeline] 布隆过滤器已重置: {spider.name}")

        logger.info(f"[BloomPipeline] 初始化: crawl_engine:dupefilter:req:{spider.name}")

    def process_item(self, item, spider):
        fp = self._get_fingerprint(item)
        if self.bloom.exists(fp):
            raise DropItem(f"重复数据(bloom): {fp[:60]}")
        self.bloom.insert(fp)
        return item

    def _get_fingerprint(self, item) -> str:
        d = dict(item)
        if d.get('item_id'):
            return str(d['item_id'])
        return '|'.join([
            str(d.get('title', '')),
            str(d.get('url', '')),
            str(d.get('pub_date', '')),
        ])
