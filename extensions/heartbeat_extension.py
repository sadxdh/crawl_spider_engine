"""
心跳扩展 - 向 Redis 写入爬虫运行状态
Key: crawl_engine:heartbeat:{spider.name}  TTL=120s
"""
import json
import os
import threading
from datetime import datetime
from scrapy import signals
from utils.redis_client import get_redis
from config import HEARTBEAT_KEY
from loguru import logger


class HeartbeatExtension:

    def __init__(self, interval: int = 30):
        self.interval = interval
        self._timer = None
        self._redis = None
        self._spider = None
        self._start_time = None

    @classmethod
    def from_crawler(cls, crawler):
        interval = crawler.settings.getint('HEARTBEAT_INTERVAL', 30)
        ext = cls(interval)
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        return ext

    def spider_opened(self, spider):
        self._spider = spider
        self._redis = get_redis()
        self._start_time = datetime.now()
        self._schedule()

    def spider_closed(self, spider):
        self._cancel()
        key = HEARTBEAT_KEY.format(spider.name)
        self._redis.delete(key)

    def _schedule(self):
        self._send()
        self._timer = threading.Timer(self.interval, self._schedule)
        self._timer.daemon = True
        self._timer.start()

    def _cancel(self):
        if self._timer:
            self._timer.cancel()

    def _send(self):
        if not self._redis or not self._spider:
            return
        try:
            key = HEARTBEAT_KEY.format(self._spider.name)
            data = {
                'spider_name': self._spider.name,
                'start_time': self._start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'last_heartbeat': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'pid': os.getpid(),
                'start_page': getattr(self._spider, 'start_page', '-'),
                'end_page': getattr(self._spider, 'end_page', '-'),
            }
            self._redis.setex(key, 120, json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.debug(f"[Heartbeat] 失败: {e}")
