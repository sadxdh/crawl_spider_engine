"""产品召回-河北省监局，来源：https://scjgj.hebei.gov.cn/col/col14517 → product_recall"""
import hashlib, re, scrapy
from lxml import etree
from spiders.base_spider import BaseSpider
from urllib.parse import urljoin
from utils.tools import *

_C = lambda v: (v[0] if isinstance(v, list) and v else v or '').strip()


class HebeiRecallSpider(BaseSpider):
    name = 'economy_recall_hebei'
    data_table = 'product_recall'
    allowed_domains = ['www.hebdprac.cn']
    proxy_type = 'long_proxy'
    custom_settings = {'CONCURRENT_REQUESTS': 8, 'DOWNLOAD_DELAY': 0.3}
    dedup_fields = ['md5_value']
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;'
                  'q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'http://www.hebdprac.cn/html/recall_xxfb_xfpzh_snzh/index_2.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0',
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            if page == 1:
                url = f'http://www.hebdprac.cn/html/recall_xxfb_xfpzh_snzh/index.html'
            else:
                url = f'http://www.hebdprac.cn/html/recall_xxfb_xfpzh_snzh/index_{page}.html'
            yield scrapy.Request(
                url=url,
                method='GET',
                headers=self.headers,
                callback=self.parse_list,
                errback=self.errback
            )

    def parse_list(self, response):
        result = etree.HTML(response.text.encode(response.encoding).decode('utf-8'))
        rows = result.xpath('//ul[@class="rg-list"]/li')
        for row in rows:
            announcement_title = row.xpath('./a/@title')[0]
            href = row.xpath('./a/@href')
            announcement_url = urljoin(response.url, href[0])
            release_date = row.xpath('./a/span/text()')[0]
            entity_name = match_text(announcement_title, pattern=r'(.*?公司|.*?厂|.*?店).*召回')
            entity_name = entity_name.split('】')[1] if entity_name and '】' in entity_name else entity_name

            temp = {'announcement_title': announcement_title, 'announcement_url': announcement_url,
                    'release_date': release_date, 'entity_name': entity_name}
            yield scrapy.Request(
                url=announcement_url,
                method='GET',
                headers=self.headers,
                callback=self.parse_detail,
                errback=self.errback,
                meta=temp
            )

    def parse_detail(self, response):
        html_node_code = get_node_html(response,
                                       content_xpath='//div[@class="xq-nr"]',
                                       rm_node_xpath=['//style'],
                                       replace_src_xpath='//div[@class="xq-nr"]/p//img'
                                       )

        announcement_title = response.meta['announcement_title']
        release_date = response.meta['release_date'].strip()
        entity_name = response.meta['entity_name']
        items = {}
        if entity_name:
            md5_value = hash_md5(release_date + entity_name + announcement_title)
            items['md5_value'] = md5_value
            items['release_date'] = release_date
            items['entity_name'] = entity_name
            items['announcement_title'] = announcement_title
            items['announcement_url'] = response.meta['announcement_url']
            items['content'] = html_node_code
            items['source'] = '河北省缺陷产品召回管理中心'
            self.log_info(items)
            yield items
    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
