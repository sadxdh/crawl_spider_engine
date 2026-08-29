"""产品召回-河南省监局，来源：https://scjgj.henan.gov.cn/col/col11457 → product_recall"""
import hashlib, re, scrapy;
from urllib.parse import urlencode

from lxml import etree;
from spiders.base_spider import BaseSpider
from utils.tools import *

_URL = 'https://scjgj.henan.gov.cn/col/col11457';
_H = {'User-Agent': 'Mozilla/5.0'}
_C = lambda v: (v[0] if isinstance(v, list) and v else v or '').strip()


class HenanRecallSpider(BaseSpider):
    name = 'economy_recall_henan'
    data_table = 'product_recall'
    allowed_domains = ['www.recall.ha.cn']
    proxy_type = 'long_proxy'
    custom_settings = {'CONCURRENT_REQUESTS': 8, 'DOWNLOAD_DELAY': 0.3}
    dedup_fields = ['md5_value']
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://www.recall.ha.cn/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            base_url = 'https://www.recall.ha.cn/news/home/search'
            params = {
                'keyword': 'sjzh',  # 省内召回
                'issearch': 'false',
                'page': str(page),
                'limit': '6',
            }
            data_url = f'{base_url}?{urlencode(params)}'
            yield scrapy.Request(
                url=data_url,
                method='GET',
                headers=self.headers,
                callback=self.parse_list,
                errback=self.errback
            )

    def parse_list(self, response):
        result = response.json()
        datas = result.get('data').get('rows')
        for data in datas:
            announcement_title = data.get('title')
            detail_id = data.get('id')
            announcement_url = f'https://www.recall.ha.cn/#/info/{detail_id}'
            release_date = data.get('fbdate')
            entity_name = match_text(announcement_title, pattern=r'(.*?公司|.*?厂|.*?店).*召回')
            entity_name = entity_name.split('】')[1] if entity_name and '】' in entity_name else entity_name

            temp = {'announcement_title': announcement_title, 'announcement_url': announcement_url,
                    'release_date': release_date, 'entity_name': entity_name, 'detail_id': detail_id}
            detail_url = 'https://www.recall.ha.cn/news/home/info'
            params = {'id': detail_id}
            data_url = f'{detail_url}?{urlencode(params)}'
            yield scrapy.Request(
                url=data_url,
                method='GET',
                headers=self.headers,
                callback=self.parse_detail,
                errback=self.errback,
                meta=temp
            )

    def parse_detail(self, response):
        result = response.json()
        content = result['data'].get('contens')
        announcement_title = response.meta['announcement_title']
        release_date = response.meta['release_date']
        entity_name = response.meta['entity_name']
        items = {}
        if entity_name:
            md5_value = hash_md5(release_date + entity_name + announcement_title)
            items['md5_value'] = md5_value
            items['release_date'] = release_date
            items['entity_name'] = entity_name
            items['announcement_title'] = announcement_title
            items['announcement_url'] = response.meta['announcement_url']
            items['content'] = content
            items['source'] = '河南省缺陷产品召回中心'
            self.log_info(items)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
