"""
随机代理中间件
读取 spider.proxy_type（由 BaseSpider 从 spider args 解析）
代理池枯竭时发送钉钉告警
"""
from utils.proxy_kit import ScrapyProxy
from utils.dingtalk import send_dd_msg
from loguru import logger


class RandomProxyMiddleware:
    """根据 spider.proxy_type 动态设置代理"""

    def __init__(self):
        self._proxy_fail_count = 0
        self._alerted = False

    def process_request(self, request, spider):
        proxy_type = getattr(spider, 'proxy_type', 'no_proxy')

        if not proxy_type or proxy_type == 'no_proxy':
            return

        proxy = ScrapyProxy.return_proxy(proxy_type)
        if proxy:
            request.meta['proxy'] = proxy
            self._proxy_fail_count = 0  # 获取成功，清零
        else:
            self._proxy_fail_count += 1
            if self._proxy_fail_count >= 10 and not self._alerted:
                logger.warning(f"[ProxyMiddleware] 代理池枯竭 ({self._proxy_fail_count}次获取失败)")
                send_dd_msg(
                    spider_name=spider.name,
                    msg_name='代理池告警',
                    msg_content=f'代理池连续 {self._proxy_fail_count} 次获取失败，代理服务可能不可用',
                )
                self._alerted = True

    def process_exception(self, request, exception, spider):
        if 'proxy' in request.meta:
            logger.warning(f"[ProxyMiddleware] 代理异常，移除后重试: {request.url[:60]}")
            del request.meta['proxy']
        return None
