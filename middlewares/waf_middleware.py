"""
WAF 绕过中间件
- RsHandlerMiddleware: 瑞数 (RS) 412 绕过 (nmpa.gov.cn)
- JslHandlerMiddleware: 加速乐 (JSL) 521 绕过
- PbcCookieMiddleware: 人民银行 Cookie 验证
"""
import json
from urllib.parse import urljoin, urlparse

import requests
from curl_cffi import requests as cr
from lxml import etree
from scrapy import Request
from scrapy.http import HtmlResponse

from utils.node_client import node_client


class RsHandlerMiddleware:
    """瑞数 WAF 绕过 — 处理 412 响应（如 nmpa.gov.cn）"""

    def __init__(self, settings):
        self.session = requests.Session()

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_request(self, request, spider):
        return None

    def process_response(self, request, response, spider):
        if response.status not in (412, 202):
            return response

        try:
            headers = self._decode_headers(request)
            url = request.url

            # 第一次请求获取 challenge
            resp = self._sync_get(url, headers)
            if not resp or resp.status_code not in (412, 202):
                return response

            # 解析 RS challenge
            meta_content, ts_code, link_url, website_info = self._parse_challenge(resp, url)
            if not meta_content or not link_url:
                spider.logger.warning(f'[{spider.name}] RS 412 解析失败: {url}')
                return response

            # 获取外链 JS
            link_resp = self._sync_get(link_url, headers)
            if not link_resp:
                return response
            link_code = link_resp.text

            # 调用 Node 服务生成 Cookie
            cookie_result = self._generate_cookie(url, meta_content, ts_code, link_code, website_info)
            if not cookie_result:
                spider.logger.warning(f'[{spider.name}] RS Cookie 生成失败: {url}')
                return response

            cookies = cookie_result.get('value', {})
            if not cookies:
                return response

            # 设置 Cookie 并重新请求
            self.session.cookies.update(cookies)
            final_resp = self._sync_get(url, headers)
            if final_resp and final_resp.status_code == 200:
                spider.logger.info(f'[{spider.name}] RS 412 绕过成功: {url}')
                return HtmlResponse(
                    url=final_resp.url,
                    status=200,
                    body=final_resp.content,
                    encoding='utf-8',
                    request=request,
                )
        except Exception as e:
            spider.logger.error(f'[{spider.name}] RS 中间件异常: {e}')

        return response

    def _parse_challenge(self, response, base_url):
        try:
            tree = etree.HTML(response.text)
            meta_content = tree.xpath('//meta[2]/@content')[0].replace("'", '')
            ts_code = tree.xpath('//script/text()')[0]
            link_path = tree.xpath('//script/@src')[0]
            link_url = urljoin(base_url, link_path)
            parsed = urlparse(base_url)
            website_info = {
                'href': base_url,
                'src': link_path,
                'origin': f'{parsed.scheme}://{parsed.netloc}',
                'host': parsed.netloc,
                'hostname': parsed.netloc.split(':')[0],
                'protocol': f'{parsed.scheme}:',
                'pathname': parsed.path,
            }
            return meta_content, ts_code, link_url, website_info
        except Exception:
            return None, None, None, None

    def _generate_cookie(self, url, meta_content, ts_code, link_code, website_info):
        try:
            result = node_client.exec_ts(
                'rs_decrypt',
                {
                    'meta_content': meta_content,
                    'ts_code': ts_code,
                    'link_code': link_code,
                    'website_info': website_info,
                },
                timeout=30,
            )
            return result
        except Exception:
            return None

    def _sync_get(self, url, headers):
        try:
            return self.session.get(url, headers=headers, timeout=30, allow_redirects=True)
        except Exception:
            return None

    @staticmethod
    def _decode_headers(request):
        return {k.decode('utf-8'): v[0].decode('utf-8') for k, v in request.headers.items()}


class JslHandlerMiddleware:
    """加速乐 (JSL) 521 绕过 — 使用 utils/jiasule.py"""

    def process_response(self, request, response, spider):
        if response.status != 521:
            return response

        try:
            from utils.jiasule import solve_jsl

            headers = {k.decode('utf-8'): v[0].decode('utf-8') for k, v in request.headers.items()}
            session = cr.Session()
            ok = solve_jsl(session, request.url, headers)
            if not ok:
                return response

            final = session.get(request.url, headers=headers, impersonate='chrome124', timeout=30)
            if final.status_code == 200:
                spider.logger.info(f'[JslHandler] 521 绕过成功: {request.url}')
                return HtmlResponse(
                    url=str(final.url), status=200, body=final.content,
                    encoding='utf-8', request=request,
                )
        except Exception as e:
            spider.logger.warning(f'[JslHandler] {request.url}: {e}')

        return response


class PbcCookieMiddleware:
    """人民银行 Cookie 验证中间件"""

    def __init__(self):
        self.cookie = None
        self.session = requests.Session()

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider):
        headers = self._decode_headers(request)
        if not self.cookie:
            try:
                result = node_client.get_cookie('pbc', timeout=30)
                if result and result.get('cookies'):
                    self.cookie = result['cookies']
            except Exception as e:
                spider.logger.warning(f'[{spider.name}] PBC Cookie 获取失败: {e}')
                return None

        if self.cookie:
            try:
                resp = self.session.get(request.url, headers=headers, cookies=self.cookie, timeout=30)
                resp.encoding = resp.apparent_encoding or 'utf-8'
                if 'Please enable JavaScript' not in resp.text:
                    return HtmlResponse(
                        url=resp.url,
                        status=resp.status_code,
                        body=resp.content,
                        encoding='utf-8',
                        request=request,
                    )
                self.cookie = None
            except Exception:
                pass
        return None

    def process_response(self, request, response, spider):
        return response

    @staticmethod
    def _decode_headers(request):
        return {k.decode('utf-8'): v[0].decode('utf-8') for k, v in request.headers.items()}
