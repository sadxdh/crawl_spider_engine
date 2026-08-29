"""产品召回-福建省监局，来源：https://scjgj.fujian.gov.cn/zw/tzgg → product_recall"""
import hashlib, re, scrapy
from lxml import etree
from spiders.base_spider import BaseSpider
from utils.tools import *
from urllib.parse import urljoin

_URL = 'https://scjgj.fujian.gov.cn/zw/tzgg'
_H = {'User-Agent': 'Mozilla/5.0'}
_C = lambda v: (v[0] if isinstance(v, list) and v else v or '').strip()


class FujianRecallSpider(BaseSpider):
    name = 'economy_recall_fujian'
    data_table = 'product_recall'
    allowed_domains = ['scjgj.fujian.gov.cn']
    proxy_type = 'long_proxy'
    dedup_fields = ['md5_value']
    custom_settings = {'CONCURRENT_REQUESTS': 8, 'DOWNLOAD_DELAY': 0.3}
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://scjgj.fujian.gov.cn',
        'Referer': 'https://scjgj.fujian.gov.cn/zt/qxcpzhxx/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            base_url = 'https://scjgj.fujian.gov.cn/fjdzapp/search'
            formdata = {
                'channelid': '229105',
                'sortfield': '-docorderpri,-docreltime',
                'classsql': 'chnlid=39794',
                'classcol': 'publishyear',
                'classnum': '100',
                'classsort': '0',
                'cache': 'true',
                'page': str(page),
                'prepage': '75',
            }
            yield scrapy.FormRequest(
                url=base_url,
                method='POST',
                formdata=formdata,
                headers=self.headers,
                callback=self.parse_list,
                errback=self.errback
            )

    def parse_list(self, response):
        result = response.json()
        datas = result.get('data')
        for data in datas:
            announcement_title = data.get('doctitle')
            announcement_url = data.get('docpuburl')
            release_date = data.get('docreltime').split(' ')[0]
            entity_name = match_text(announcement_title, pattern=r'(.*?公司|.*?厂|.*?店).*召回')
            entity_name = entity_name.split('】')[1] if entity_name and '】' in entity_name else entity_name
            temp = {'announcement_title': announcement_title, 'announcement_url': announcement_url,
                    'release_date': release_date, 'entity_name': entity_name}
            yield scrapy.Request(
                url=announcement_url,
                method="GET",
                callback=self.parse_detail,
                headers=self.headers,
                errback=self.errback,
                meta=temp
            )

    def parse_detail(self, response):
        content = get_node_html(response,
                                content_xpath='//div[@class="TRS_Editor"]',
                                replace_src_xpath='//div[@class="TRS_Editor"]/p/img'
                                )

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
            items['source'] = '福建市场监督管理局'
            self.log_info(items)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
