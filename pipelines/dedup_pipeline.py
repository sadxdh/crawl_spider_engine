"""
批次内内存去重 Pipeline (Priority=100)

同一批次内如有相同去重键只保留第一条。数据库去重由 MysqlPipeline upsert 处理。
"""

from loguru import logger


class DedupPipeline:

    def open_spider(self, spider):
        self.fields = getattr(spider, 'dedup_fields', [])
        self._cache = set()
        if not self.fields:
            logger.info(f"[DedupPipeline] {spider.name} 未设置 dedup_fields")
        else:
            logger.info(f"[DedupPipeline] {spider.name} 去重字段: {self.fields}")

    def process_item(self, item, spider):
        d = dict(item)

        if not self.fields:
            if 'md5_value' in d and d['md5_value']:
                self.fields = ['md5_value']
            elif 'keyno' in d and d['keyno']:
                self.fields = ['keyno']
            else:
                return item

        # 同批次内存去重
        cache_key = tuple(str(d.get(f, '')) for f in self.fields)
        if cache_key in self._cache:
            spider.crawler.stats.inc_value('pipeline/dedup_batch')
            return None
        self._cache.add(cache_key)

        return item
