"""
HTTP 错误处理中间件（Spider中间件）
参考: yuncrawl/crawl/middlewares/base_middlewares.py HttpError(543)
"""
from scrapy.spidermiddlewares.httperror import HttpErrorMiddleware as BaseHttpError
from loguru import logger


class HttpErrorMiddleware(BaseHttpError):
    """处理 HTTP 错误响应，记录日志"""

    def process_spider_exception(self, response, exception, spider):
        logger.warning(
            f"[HttpError] {spider.name} - {response.status} - {response.url[:100]}"
        )
        return None
