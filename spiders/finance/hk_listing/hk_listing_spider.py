"""港股上市爬虫，来源：东方财富"""
import scrapy
from spiders.base_spider import BaseSpider
from urllib.parse import urlencode

from utils.mysql_tools import select_data
from utils.tools import *

# data_crawl_server spider/finance/hk_listing/main.py
class HkListingSpider(BaseSpider):
    name = 'finance_hk_listing'
    data_table = 'stock_hk'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 1, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        },
        "RETRY_HTTP_CODES": [408, 429, 500, 502, 503, 504],
    }
    proxy_type = 'long_proxy'

    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'referer': 'https://www.hkex.com.hk/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    }
    datas_list = []

    finished_pages = 0

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            params = {
                'np': '1',
                'fltt': '1',
                'invt': '2',
                'fs': 'm:128+t:3,m:128+t:4,m:128+t:1,m:128+t:2',
                'fields': 'f12,f14',
                'fid': 'f12',
                'pn': str(page),
                'pz': '100',
                'po': '0',
                'dect': '1',
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'wbp2u': '|0|0|0|web',
            }
            url = 'https://push2.eastmoney.com/api/qt/clist/get'
            request_url = f'{url}?{urlencode(params)}'
            yield scrapy.Request(
                url=request_url,
                method='GET',
                headers=self.headers,
                callback=self.parse_list,
                dont_filter=True,
            )

    def parse_list(self, response):
        result = response.json()
        datas = result['data']['diff']
        for data in datas:
            entity_id = data['f12']
            entity_name = data['f14']
            md5_value = hash_md5(str(entity_id) + entity_name)
            data_list = {'entity_id': entity_id, 'entity_name': entity_name, 'md5_value': md5_value}
            self.datas_list.append(data_list)
            yield from self.save_data(data_list)

        self.finished_pages += 1
        if self.finished_pages == self.end_page:
            yield from self.update_data()




    def save_data(self, data):
        entity_id = data['entity_id']
        entity_name = data['entity_name']
        md5_value = data['md5_value']
        # is_exist = select_data(table='stock_hk', data=['id'], condition=f'md5_value="{md5_value}"')
        # status = 1 if is_exist else 0
        status = 1

        items = {}
        items['entity_id'] = entity_id
        items['entity_name'] = entity_name
        items['status'] = status
        items['md5_value'] = md5_value
        # insert_data('stock_hk', item)
        yield items


    def update_data(self):
        crawl_data = [data['md5_value'] for data in self.datas_list]
        table_datas = select_data(table='stock_hk', data=['md5_value'])
        table_md5 = [data['md5_value'] for data in table_datas]
        for md5_value in table_md5:
            if md5_value not in crawl_data:
                items = {'status': 0, 'md5_value': md5_value}
                # update_data(table_name='stock_hk', data={'status': 0, 'md5_value': md5_value}, condition=f'md5_value="{md5_value}"')
                yield items

    def errback(self, failure): self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
