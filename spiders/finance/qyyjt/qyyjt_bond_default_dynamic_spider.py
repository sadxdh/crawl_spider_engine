"""
企业预警通 — 债券违约动态爬虫
数据来源：https://www.qyyjt.cn/default/bondDefault/dynamic
API：POST https://www.qyyjt.cn/getData.action?_t=780

增量策略：
  - 每页50条
  - 增量：start_page=1 end_page=2（最新100条）
  - 去重字段：md5_value（bond_abbr + dynamic_title + dynamic_date 的 md5）

本地调试：
  scrapy crawl finance_qyyjt_bond_default_dynamic -a start_page=1 -a end_page=2
"""
from urllib.parse import urlencode

import scrapy
from utils.tools import *
from spiders.finance.qyyjt.qyyjt_base_spider import QyyjtBaseSpider


class QyyjtBondDefaultDynamicSpider(QyyjtBaseSpider):
    """企业预警通债券违约动态爬虫"""

    name = 'finance_qyyjt_bond_default_dynamic'
    data_table = 'bond_default_dynamic'
    dedup_fields = ['md5_value']

    custom_settings = {
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 3,
        'DEFAULT_REQUEST_HEADERS': {},
    }

    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cache-control': 'no-cache',
        'client': 'pc-web;pro',
        'dataid': '780',
        'origin': 'https://www.qyyjt.cn',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://www.qyyjt.cn/default/bondDefault/dynamic',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'system': 'new',
        'system1': 'Windows NT 10.0; Win64; x64;Chrome;133.0.0.0',
        'terminal': 'pc-web;pro',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/133.0.0.0 Safari/537.36',
        'ver': '20250218',
    }

    base_url = 'https://www.qyyjt.cn/getData.action'

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            skip = self.page_to_skip(page)
            headers = self._get_auth_headers(self.headers)
            if not headers:
                self.log_warning(f'第 {page} 页无 token，跳过')
                continue
            yield scrapy.Request(
                url=self.base_url,
                method='POST',
                headers=headers,
                body=f'skip={skip}&pagesize=50&_t=780',
                callback=self.parse_list,
                errback=self.errback,
                meta={'page': page, 'skip': skip},
                dont_filter=True,
            )

    def parse_list(self, response):
        result = response.json()['data']
        for data in result:
            bond_code = data.get('bond_code')
            bond_abbr = data.get('bondAbbr')
            dynamic_title = data['dynamic_title']
            dynamic_date = data['default_time']
            dynamic_status = data['dynamic_status']
            md5_value = hash_md5(bond_abbr + dynamic_title + dynamic_date)

            items = {}
            items['bond_code'] = bond_code
            items['bond_abbr'] = bond_abbr
            items['dynamic_title'] = dynamic_title
            items['dynamic_date'] = dynamic_date
            items['dynamic_status'] = dynamic_status
            items['md5_value'] = md5_value
            items['_table'] = 'bond_default_dynamic'
            # insert_data('bond_default_dynamic', item)
            yield items

            bond_full_code = data['BondCode']
            # self.course_list.append(bond_full_code)
            headers = self._get_auth_headers(self.headers)
            params = {
                'BondCode': bond_full_code,
                'skip': '0',
                'pagesize': '999',
                '_t': '780',
            }
            url = f"{self.base_url}?{urlencode(params)}"

            yield scrapy.Request(
                url=url,
                method="POST",
                headers=headers,
                callback=self.parse_course_data,
            )

    def parse_course_data(self, response):
        result = response.json().get('data', [])
        for data in result:
            bond_code = data['bond_code']
            bond_abbr = data['bondAbbr']
            dynamic_title = data.get('dynamic_title')
            dynamic_date = data.get('default_time')
            dynamic_status = data.get('dynamic_status')

            md5_value = hash_md5(bond_abbr + dynamic_title + dynamic_date)

            items = {}
            items['bond_code'] = bond_code
            items['bond_abbr'] = bond_abbr
            items['dynamic_title'] = dynamic_title
            items['dynamic_date'] = dynamic_date
            items['dynamic_status'] = dynamic_status
            items['md5_value'] = md5_value
            # insert_data('bond_default_dynamic', item)
            items['_table'] = 'bond_default_dynamic'
            yield items