"""
curl_cffi 下载中间件 — 使用浏览器 TLS 指纹绕过反爬
- moj.gov.cn → chrome124
- sbj.cnipa.gov.cn → safari17_0 (商标局)
- nmpa.gov.cn → chrome124
- bse.cn → chrome124 (北交所, 302+C3VK cookie 反爬)
"""
from curl_cffi import requests as curl_requests
from scrapy import signals
from scrapy.http import HtmlResponse


class CurlCffiMiddleware:
    """对特定域名使用 curl_cffi 发起请求，模拟浏览器 TLS 指纹"""

    # 域名 → 模拟目标 映射
    DOMAIN_IMPERSONATE = {
        'moj.gov.cn': 'chrome124',
        'sbj.cnipa.gov.cn': 'safari17_0',
        'nmpa.gov.cn': 'chrome124',
        'cbex.com.cn': 'chrome124',
        'suaee.com': 'chrome124',
        'sotcbb.com': 'chrome124',
        'cneptp.com': 'chrome124',
        'gs.amac.org.cn': 'chrome124',
        'chinatax.gov.cn': 'chrome124',
        'beijing.chinatax.gov.cn': 'chrome124',
        'landchina.mnr.gov.cn': 'chrome124',
        'hshfy.sh.cn': 'chrome124',
        'bse.cn': 'chrome124',
    }

    def __init__(self):
        self._session = None

    @classmethod
    def from_crawler(cls, crawler):
        mw = cls()
        crawler.signals.connect(mw.spider_opened, signal=signals.spider_opened)
        return mw

    def spider_opened(self, spider):
        self._session = curl_requests.Session()

    def process_request(self, request, spider):
        if not self._session:
            return None

        impersonate = None
        for domain, target in self.DOMAIN_IMPERSONATE.items():
            if domain in request.url:
                impersonate = target
                break
        if not impersonate:
            return None

        headers = {k.decode('utf-8'): v[0].decode('utf-8') for k, v in request.headers.items()}
        # 读取代理设置（由 RandomProxyMiddleware 在 process_request 中设置）
        proxy = request.meta.get('proxy') or {}
        if isinstance(proxy, str):
            proxy = {'http': proxy, 'https': proxy}
        try:
            if request.method == 'POST':
                resp = self._session.post(
                    request.url,
                    headers=headers,
                    data=request.body,
                    impersonate=impersonate,
                    timeout=30,
                    allow_redirects=True,
                    proxies=proxy if proxy else None,
                )
            else:
                resp = self._session.get(
                    request.url,
                    headers=headers,
                    impersonate=impersonate,
                    timeout=30,
                    allow_redirects=True,
                    proxies=proxy if proxy else None,
                )
            return HtmlResponse(
                url=str(resp.url),
                status=resp.status_code,
                body=resp.content,
                encoding='utf-8',
                request=request,
            )
        except Exception as e:
            spider.logger.warning(f'[CurlCffiMiddleware] {request.url}: {e}')
            return None
