"""
重试中间件：超过重试次数后记录 warning 日志
"""
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message
from loguru import logger


class RetryAlarmMiddleware(RetryMiddleware):

    def process_response(self, request, response, spider):
        if request.meta.get('dont_retry', False):
            return response

        if response.status in self.retry_http_codes:
            reason = response_status_message(response.status)
            retry_times = request.meta.get('retry_times', 0)

            if retry_times >= self.max_retry_times:
                logger.warning(
                    f"[RetryAlarm] 重试耗尽: {request.url} "
                    f"状态码={response.status} 已重试={retry_times}次"
                )

            return self._retry(request, reason, spider) or response

        return response

    def process_exception(self, request, exception, spider):
        result = super().process_exception(request, exception, spider)

        retry_times = request.meta.get('retry_times', 0)
        if retry_times >= self.max_retry_times:
            logger.warning(
                f"[RetryAlarm] 请求异常: {request.url} "
                f"{type(exception).__name__}: {exception}"
            )

        return result
