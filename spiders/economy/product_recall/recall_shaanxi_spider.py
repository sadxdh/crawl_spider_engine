"""产品召回-陕西省监局，来源：https://snamr.shaanxi.gov.cn/zwgk/tzgg → product_recall"""
import hashlib, re, scrapy;
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *

_C = lambda v: (v[0] if isinstance(v, list) and v else v or '').strip()


class ShaanxiRecallSpider(BaseSpider):
    name = 'economy_recall_shaanxi'
    data_table = 'product_recall'
    allowed_domains = ['www.sxdpac.com']
    proxy_type = 'long_proxy'
    custom_settings = {'CONCURRENT_REQUESTS': 8, 'DOWNLOAD_DELAY': 0.3}
    dedup_fields = ['md5_value']
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Content-Type': 'application/json',
        'Referer': 'http://www.sxdpac.com/html/articleListZh.html?type=2&recallType=PROVINCE_CONSUMPTION',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            params = {
                'page': str(page),
                'pageSize': '10',
                'newType': 'RECALL',
                'recallType': 'PROVINCE_CONSUMPTION',
            }
            base_url = 'http://www.sxdpac.com/v1/front/new'
            url = f"{base_url}?{urlencode(params)}"
            yield scrapy.Request(
                url=url,
                headers=self.headers,
                callback=self.parse_list,
                errback=self.errback
            )

    def parse_list(self, response):
        result = response.json()
        datas = result['resultData']['newList']
        for data in datas:
            announcement_title = data.get('title')
            detail_id = data.get('newId')
            announcement_url = f'http://www.sxdpac.com/html/articleDetail.html?newId={detail_id}'
            release_date = data.get('createTime').split(' ')[0]
            entity_name = match_text(announcement_title, pattern=r'(.*?公司|.*?厂|.*?店).*召回')
            entity_name = entity_name.split('】')[1] if entity_name and '】' in entity_name else entity_name

            temp = {'announcement_title': announcement_title, 'announcement_url': announcement_url,
                    'release_date': release_date, 'entity_name': entity_name, 'detail_id': detail_id}
            yield scrapy.Request(
                url=f'http://www.sxdpac.com/v1/front/new/{detail_id}',
                headers=self.headers,
                callback=self.parse_detail,
                errback=self.errback,
                cb_kwargs={'parms': temp}
            )

    def parse_detail(self, response, parms):
        result = response.json()['resultData']
        content = result['detail']
        announcement_title = parms['announcement_title']
        release_date = parms['release_date'].strip()
        entity_name = parms['entity_name']
        items = {}
        if entity_name:
            md5_value = hash_md5(release_date + entity_name + announcement_title)
            items['md5_value'] = md5_value
            items['release_date'] = release_date
            items['entity_name'] = entity_name
            items['announcement_title'] = announcement_title
            items['announcement_url'] = parms['announcement_url']
            items['content'] = content
            items['source'] = '山西省缺陷产品召回中心'
            self.log_info(items)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
