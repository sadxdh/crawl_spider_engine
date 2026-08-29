"""产品召回-广东省监局，来源：https://amr.gd.gov.cn/zwgk/zdlyxxgk/cpzhxx/content/post_{page}.html → product_recall"""
import hashlib, re, scrapy
from lxml import etree
from spiders.base_spider import BaseSpider
from utils.tools import *
from urllib.parse import urljoin

_URL = 'https://amr.gd.gov.cn/zwgk/zdlyxxgk/cpzhxx/content/post_{page}.html'
_H = {'User-Agent': 'Mozilla/5.0'}
_C = lambda v: (v[0] if isinstance(v, list) and v else v or '').strip()


class GuangdongRecallSpider(BaseSpider):
    name = 'economy_recall_guangdong'
    data_table = 'product_recall'
    allowed_domains = ['amr.gd.gov.cn']
    proxy_type = 'long_proxy'
    custom_settings = {'CONCURRENT_REQUESTS': 8, 'DOWNLOAD_DELAY': 0.3}
    dedup_fields = ['md5_value']
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;'
                  'q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'http://amr.gd.gov.cn/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/129.0.0.0 Safari/537.36',
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            url = _URL
            if page == 1:
                url = f'http://amr.gd.gov.cn/zwgk/zdlyxxgk/zhxx/xfpzh/index.html'
            else:
                url = f'http://amr.gd.gov.cn/zwgk/zdlyxxgk/zhxx/xfpzh/index_{page}.html'
            yield scrapy.Request(
                url=url,
                method='GET',
                headers=self.headers,
                callback=self.parse_list,
                errback=self.errback
            )

    def parse_list(self, response):
        result = etree.HTML(response.text.encode(response.encoding).decode('utf-8'))
        rows = result.xpath('//ul[@class="news_list2 marB20"]/li')
        for row in rows:
            announcement_title = row.xpath('./h3/a/text()')[0]
            href = row.xpath('./h3/a/@href')
            announcement_url = urljoin(response.url, href[0])
            release_date = row.xpath('./span/text()')[0]
            entity_name = match_text(announcement_title, pattern=r'(.*?公司|.*?厂|.*?店|.*?部).*召回')
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
        html_node_code = get_node_html(response, content_xpath='//div[@class="article"]', replace_href_xpath='//div[@class="article"]//p/a')
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
            items['source'] = '广东省市场监督管理委员局'
            self.log_info(items)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
