"""
Requests 下载中间件 — 使用 Python requests 库替代 Twisted
避免 TLS 指纹被目标网站识别拦截
"""
import requests as req
from scrapy.http import HtmlResponse


class RequestsMiddleware:
    """对特定域名使用 Python requests 请求（与旧项目 TLS 指纹一致）"""

    DOMAINS = ['gs.amac.org.cn']

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider):
        if not any(d in request.url for d in self.DOMAINS):
            return None

        headers = {k.decode('utf-8'): v[0].decode('utf-8') for k, v in request.headers.items()}
        # 确保 Content-Type 为 JSON
        if request.method == 'POST' and 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
        try:
            if request.method == 'POST':
                body = request.body
                if isinstance(body, bytes):
                    body = body.decode('utf-8')
                r = req.post(request.url, headers=headers, data=body or '{}', timeout=30)
            else:
                r = req.get(request.url, headers=headers, timeout=30)
            r.encoding = r.apparent_encoding or 'utf-8'
            return HtmlResponse(url=str(r.url), status=r.status_code, body=r.content,
                                encoding=r.encoding or 'utf-8', request=request)
        except Exception as e:
            spider.logger.warning(f'[RequestsMW] {request.url}: {e}')
            return None
