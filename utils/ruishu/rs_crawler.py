from utils.tools import *
from loguru import logger
from tenacity import RetryError, Retrying, AsyncRetrying, stop_after_attempt
from config import *

class RsRequest():
    spider_name = 'rs_request'

    def __init__(self):
        super().__init__()
        self.session = requests.Session()

    @staticmethod
    def parse_url(url):
        parsed = urlparse(url)
        # 协议
        scheme = parsed.scheme
        protocol = scheme + ":"
        # 主机（不含端口）
        netloc = parsed.netloc
        if ':' in netloc and not netloc.endswith(']'):  # 避免 IPv6 误判
            hostname = netloc.rsplit(':', 1)[0]
        else:
            hostname = netloc
        # origin = scheme + "://" + netloc（注意：包含端口）
        origin = f"{scheme}://{netloc}"
        # 路径
        pathname = parsed.path
        return {
            'origin': origin,
            'host': hostname,
            'hostname': hostname,
            'protocol': protocol,
            'pathname': pathname
        }

    def rs_request(self, url, headers, proxy_enable=False):
        if proxy_enable:
            proxies = ScrapyProxy.get_long_proxy()
            self.session.proxies = proxies

        response = self.session_request(self.session, url=url, headers=headers)
        if response.text and response.status_code in [202, 412]:
            try:
                tree = etree.HTML(response.text)
                meta_content = tree.xpath('//meta[2]/@content')[0].replace("'", '')
                ts_code = tree.xpath('//script/text()')[0]
                link_url = tree.xpath('//script/@src')[0]
                new_link_url = urljoin(response.url, link_url)
                website_info = {"href": url, "src": link_url}
                parse_result = self.parse_url(url)
                website_info.update(parse_result)
            except Exception as e:
                logger.error(f'{self.spider_name} 瑞数解析第一次请求错误:{e}')
            else:
                # 获取外链js
                content_response = self.session_request(self.session, url=new_link_url, headers=headers)
                if content_response:
                    link_code = content_response.text
                    # 请求rs接口
                    decrypt_response = self.generate_rs_cookie(meta_content, ts_code, link_code, website_info)
                    if decrypt_response:
                        result = decrypt_response.json()
                        cookie = result.get('value', {})
                        if cookie:
                            self.session.cookies.update(cookie)
                            # 第二次请求
                            finally_response = self.session_request(self.session, url=url, headers=headers)
                            return finally_response
        else:
            return response

    def session_request(self, session,
        url,
        headers,
        method='get',
        params=None,
        data=None,
        json_data=None,
        verify: bool = False,
        timeout: int = 60,
        allow_redirects=True,
        # 新增参数
        max_retries: int = 3,
    ):
        logger.debug('session_request url: %s, proxy: %s' % (url, session.proxies))

        try:
            response = self.get_session_response(
                session=session,
                url=url,
                headers=headers,
                method=method,
                params=params,
                data=data,
                json=json_data,
                verify=verify,
                timeout=timeout,
                allow_redirects=allow_redirects,
                max_retries=max_retries,
            )
        except RetryError as e:
            response = None
            error_msg = f'请求超出重试次数, url:{url}, e: {e.last_attempt.exception()}'
            logger.error(error_msg)
        return response

    @staticmethod
    def get_session_response(session, **kwargs):
        """session 请求"""
        url = kwargs.get('url')
        max_retries = kwargs.pop('max_retries')

        for attempt in Retrying(stop=stop_after_attempt(max_retries)):
            with attempt:
                try:
                    response = session.request(**kwargs)
                    return response
                except (requests.exceptions.RequestException, Exception) as e:
                    logger.error('[error] Attempt {} failed for url: {}, error: {}', attempt.retry_state.attempt_number,
                                 url, e)
                    raise e

    def generate_rs_cookie(self, meta_content, ts_code, link_code, website_info: dict):
        url = NODE_CONF['exec_ck_url']
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0'
        }
        data = {
            "meta_content": meta_content,
            "ts_code": ts_code,
            "link_code": link_code,
            "website_info": json.dumps(website_info, ensure_ascii=False)
        }
        response = requests.request(
            url=url,
            method='post',
            headers=headers,
            data=data
        )
        return response
