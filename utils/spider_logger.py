"""
爬虫日志模块 — 扩展输出，不覆盖Scrapy系统日志

用法:
    from utils.spider_logger import get_logger

    class MySpider(BaseSpider):
        def parse(self, response):
            self.log.info('开始解析')
            self.log.item('产出数据')
"""

import time
from loguru import logger as _loguru


class SpiderLogger:
    """爬虫日志器，按 spider 实例隔离"""

    DROP_FILTER = {
        '数据库已存在', '批次内重复', '重复数据(bloom)', '入库失败',
        'Dropped', 'DropItem',
    }

    def __init__(self, name: str):
        self.name = name
        self._start = time.time()
        self.pages = 0
        self.items = 0
        self.errors = 0
        self.dropped = 0

    def _tag(self, msg: str) -> str:
        t = int(time.time() - self._start)
        return f"[{self.name}][{t}s] {msg}"

    def info(self, msg: str):
        _loguru.info(self._tag(msg))

    def warning(self, msg: str):
        _loguru.warning(self._tag(msg))

    def error(self, msg: str):
        _loguru.error(self._tag(msg))
        self.errors += 1

    def debug(self, msg: str):
        _loguru.debug(self._tag(msg))

    def item(self, msg: str = ''):
        """产出一条数据"""
        self.items += 1
        _loguru.debug(self._tag(f"+item {msg}" if msg else "+item"))

    def drop(self, reason: str = ''):
        """去重丢弃，精简输出不打印详情"""
        self.dropped += 1
        # 静默处理，不打印item内容

    def page(self, n: int, msg: str = ''):
        """处理完一页"""
        self.pages += n
        _loguru.debug(self._tag(f"page#{n} {msg}".strip()))

    def request_error(self, url: str, err: str):
        self.errors += 1
        _loguru.error(self._tag(f"请求失败: {url[:100]} — {err}"))

    def parse_error(self, detail: str = ''):
        self.errors += 1
        _loguru.error(self._tag(f"解析失败: {detail}"))

    def summary(self):
        t = int(time.time() - self._start)
        p = self.pages
        i = self.items
        e = self.errors
        d = self.dropped
        _loguru.info(
            f"[{self.name}] {'='*20} 结束 {'='*20}")
        _loguru.info(
            f"[{self.name}] 耗时={t}s | 页数={p} | 产出={i} | 去重={d} | 错误={e}")


# 全局 logger 工厂
def get_logger(name: str) -> SpiderLogger:
    return SpiderLogger(name)
