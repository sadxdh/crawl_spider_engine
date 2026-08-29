"""人民法院案例库爬虫
来源: data_crawl_server law_case/rmfy/rmfy_case.py + generate_cookie.py
API: rmfyalk.court.gov.cn (需 OAuth 登录)
"""
import json, hashlib, random, urllib.parse
import scrapy
from spiders.base_spider import BaseSpider
from spiders.law.law_case_auth import generate_cookie
from utils.admin_account_client import account_client

_API = 'https://rmfyalk.court.gov.cn/cpws_al_api/api/cpwsAl/search'

_HEADERS = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Content-Type': 'application/json;charset=UTF-8',
    'Origin': 'https://rmfyalk.court.gov.cn',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142.0.0.0 Safari/537.36',
}


class LawCaseSpider(BaseSpider):
    name = 'law_case'
    data_table = 'spider_case_raw'
    allowed_domains = ['rmfyalk.court.gov.cn', 'account.court.gov.cn']
    dedup_fields = ['md5_value']

    custom_settings = {
        'CONCURRENT_REQUESTS': 2,
        'DOWNLOAD_DELAY': 1,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cookies = None

    def _get_auth_cookies(self):
        """从平台凭证管理获取账号并生成 OAuth cookies"""
        try:
            acc = account_client.acquire('law_case')
            if not acc or not acc.get('phone'):
                self.log_warning('无 law_case 账号')
                return None
            phone = acc['phone']
            password = acc.get('password', '')
            self.log_info(f'law_case 使用账号: {phone}')
            cookies = generate_cookie(phone, password)
            if cookies:
                self.log_info('law_case cookie 获取成功')
                return cookies
            self.log_warning('law_case cookie 获取失败')
        except Exception as e:
            self.log_error(f'law_case auth error: {e}')
        return None

    def start_requests(self):
        self._cookies = self._get_auth_cookies()
        if not self._cookies:
            self.log_warning('无有效 cookies，跳过')
            return

        # 将 cookie 转为请求头以确保发送
        cookie_hdr = '; '.join(f'{k}={v}' for k, v in self._cookies.items())
        hdrs = dict(_HEADERS)
        hdrs['Cookie'] = cookie_hdr

        for page in range(self.start_page, self.end_page + 1):
            yield scrapy.Request(
                url=_API, method='POST', headers=hdrs,
                body=json.dumps({
                    'page': page, 'size': 50, 'lib': 'qb',
                    'searchParams': {
                        'userSearchType': 1, 'isAdvSearch': '0',
                        'selectValue': 'qw', 'lib': 'cpwsAl_qb', 'sort_field': '',
                    },
                }),
                callback=self.parse, errback=self.errback, meta={'page': page},
            )

    def parse(self, response):
        try:
            data = response.json()
        except Exception:
            return
        for row in (data.get('data') or {}).get('datas') or []:
            title = row.get('cpws_al_title', '')
            if not title:
                continue
            case_id = row.get('id', '')
            case_sort = row.get('cpws_al_case_sort_name', '')
            court_sort = row.get('cpws_al_sort_name', '')
            case_type = f'{case_sort}-{court_sort}'
            web_url = f'https://rmfyalk.court.gov.cn/view/content.html?id={case_id}&lib=ck'
            md5_value = hashlib.md5((title + '人民法院案例库').encode()).hexdigest()

            # 写入 spider_case_raw
            yield {
                'web_name': '人民法院案例库',
                'web_url': web_url,
                'main_type': 1,
                'case_type': case_type,
                'title': title,
                'main_info': row.get('cpws_al_infos', ''),
                'judgment_essence': row.get('cpws_al_cpyz', ''),
                'pdf_url': '',
                'md5_value': md5_value,
                '_table': 'spider_case_raw',
            }

            # 请求详情内容 API → case_parse_main
            encoded_url_id = urllib.parse.quote(case_id)
            cookie_hdr = '; '.join(f'{k}={v}' for k, v in (self._cookies or {}).items())
            detail_hdrs = dict(_HEADERS)
            detail_hdrs['Cookie'] = cookie_hdr
            detail_hdrs['Referer'] = f'https://rmfyalk.court.gov.cn/view/content.html?id={encoded_url_id}&lib=ck'
            yield scrapy.Request(
                url='https://rmfyalk.court.gov.cn/cpws_al_api/api/cpwsAl/content',
                method='POST', headers=detail_hdrs,
                body=json.dumps({'gid': case_id}),
                callback=self._parse_content, errback=self.errback,
                meta={
                    'web_url': web_url, 'case_type': case_type,
                    'court_name': row.get('cpws_al_slfy_name', ''),
                    'trial_year': row.get('cpws_al_zs_date', ''),
                    'case_level': row.get('cpws_al_type', ''),
                    'trial_procedure': row.get('cpws_al_slcx_name', ''),
                    'md5_value': md5_value,
                },
            )

    def _parse_content(self, response):
        meta = response.meta
        try:
            result = response.json()
            content = result.get('data', {}).get('data', {})
        except Exception:
            content = {}
        yield {
            'web_name': '人民法院案例库',
            'web_url': meta['web_url'],
            'case_type': meta['case_type'],
            'storage_no': content.get('cpws_al_no', ''),
            'court_name': meta['court_name'],
            'key_words': ','.join(content.get('cpws_al_keyword', [])),
            'trial_procedure': meta['trial_procedure'],
            'trial_year': meta['trial_year'],
            'case_level': meta['case_level'],
            'basic_facts': content.get('cpws_al_jbaq', ''),
            'judgment_reason': content.get('cpws_al_cply', ''),
            'judgment_essence': content.get('cpws_al_cpyz', ''),
            'judgment_mean': '',
            'judgment_result': content.get('cpws_al_cpjg', ''),
            'related_info': content.get('cpws_al_glsy', ''),
            'related_law': '',
            'related_judgment_body': '',
            'md5_value': meta['md5_value'],
            '_table': 'case_parse_main',
        }

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
