"""
统计扩展 - 每5秒将 Scrapy stats 写入 Redis
Key: yuncrawl_stats:{spider.name}（与管理平台兼容）
"""
import threading
from scrapy import signals
from utils.redis_client import get_redis
from config import STATS_KEY
from loguru import logger


class StatsExtension:
    """定期将 Scrapy stats 推送到 Redis Hash"""

    def __init__(self, stats, interval: int = 5):
        self.stats = stats
        self.interval = interval
        self._timer = None
        self._redis = None
        self._spider_name = None

    @classmethod
    def from_crawler(cls, crawler):
        interval = crawler.settings.getint('STATS_PUSH_INTERVAL', 5)
        ext = cls(crawler.stats, interval)
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        return ext

    def spider_opened(self, spider):
        self._spider_name = spider.name
        self._redis = get_redis()
        self._schedule()

    def spider_closed(self, spider):
        self._cancel()
        self._push()
        self._redis.delete(STATS_KEY.format(self._spider_name))

    def _schedule(self):
        self._push()
        self._timer = threading.Timer(self.interval, self._schedule)
        self._timer.daemon = True
        self._timer.start()

    def _cancel(self):
        if self._timer:
            self._timer.cancel()

    def _push(self):
        if not self._redis or not self._spider_name:
            return
        try:
            stats = self.stats.get_stats()
            key = STATS_KEY.format(self._spider_name)
            clean = {str(k): str(v) for k, v in stats.items()
                     if isinstance(v, (int, float, str)) or hasattr(v, 'isoformat')}
            if clean:
                self._redis.hset(key, mapping=clean)
                self._redis.expire(key, 3600)
        except Exception as e:
            logger.debug(f"[StatsExtension] 推送失败: {e}")
