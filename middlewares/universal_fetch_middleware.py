"""
通用引擎 Playwright 抓取中间件
通过 universal_engine /fetch 端点使用真实浏览器抓取 WAF 保护页面
"""
import requests as req
from scrapy.http import HtmlResponse
from config import get_config


class UniversalFetchMiddleware:
    """对特定域名使用 universal_engine Playwright 抓取"""

    # 需要使用浏览器抓取的域名
    DOMAINS = ['nmpa.gov.cn', 'pbc.gov.cn']

    def __init__(self):
        conf = get_config('dev')
        admin_conf = conf.get('ADMIN', {})
        self._api_url = admin_conf.get('api_url', 'http://backend:5000').replace('backend:5000', 'crawl_universal_engine:8100')
        self._token = admin_conf.get('api_token', 'dev_token')

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider):
        if not any(d in request.url for d in self.DOMAINS):
            return None

        try:
            headers = {'Authorization': f'Bearer {self._token}'}
            payload = {
                'url': request.url,
                'headers': {k.decode('utf-8'): v[0].decode('utf-8') for k, v in request.headers.items()},
                'timeout': 45,
            }
            resp = req.post(f'{self._api_url}/fetch', json=payload, headers=headers, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('html') and len(data['html']) > 100:
                    return HtmlResponse(
                        url=data.get('url', request.url),
                        status=data.get('status', 200),
                        body=data['html'].encode('utf-8'),
                        encoding='utf-8',
                        request=request,
                    )
        except Exception as e:
            spider.logger.warning(f'[UniversalFetch] {request.url}: {e}')
        return None
