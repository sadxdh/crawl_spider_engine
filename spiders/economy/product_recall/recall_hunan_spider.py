"""产品召回-湖南省监局，来源：https://amr.hunan.gov.cn/amr/zwgk/cpzhxx → product_recall"""
import hashlib, re, scrapy;
from lxml import etree;
from spiders.base_spider import BaseSpider
from utils.tools import *

_C = lambda v: (v[0] if isinstance(v, list) and v else v or '').strip()


class HunanRecallSpider(BaseSpider):
    name = 'economy_recall_hunan'
    data_table = 'product_recall'
    allowed_domains = ['amr.hunan.gov.cn']
    proxy_type = 'long_proxy'
    custom_settings = {
        'CONCURRENT_REQUESTS': 8,
        'DOWNLOAD_DELAY': 0.3,
        'DOWNLOADER_CLIENT_TLS_VERIFY': False
    }
    dedup_fields = ['md5_value']
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;'
                  'q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://amr.hunan.gov.cn/amr/ztx/qxcpzh/zhxx/snzh/index_2.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            if page == 1:
                url = f'https://amr.hunan.gov.cn/amr/ztx/qxcpzh/zhxx/snzh/index.html'
            else:
                url = f'https://amr.hunan.gov.cn/amr/ztx/qxcpzh/zhxx/snzh/index_{page}.html'
            response_data = curl_cffi_request(
                url=url,
                headers=self.headers,
                proxies_type=True
            )
            if response_data:
                yield from self.parse_list(response_data)

    def parse_list(self, response):
        result = etree.HTML(response.text.encode(response.encoding).decode('utf-8'))
        rows = result.xpath('//div[@class="listPage-r-li"]/ul/li')
        for row in rows:
            announcement_title = row.xpath('./a/@title')[0]
            href = row.xpath('./a/@href')
            announcement_url = urljoin(response.url, href[0])
            release_date = row.xpath('./small//text()')[0]
            entity_name = match_text(announcement_title, pattern=r'(.*?公司|.*?厂|.*?店).*召回')
            entity_name = entity_name.split('】')[1] if entity_name and '】' in entity_name else entity_name
            temp = {'announcement_title': announcement_title, 'announcement_url': announcement_url,
                    'release_date': release_date, 'entity_name': entity_name}
            response_data = curl_cffi_request(
                url=announcement_url,
                headers=self.headers,
                proxies_type=True
            )
            if response_data:
                yield from self.parse_detail(response_data, temp)

    def parse_detail(self, response, temp):
        html_node_code = get_node_html(response,
                                       content_xpath='//div[@class="text"]',
                                       replace_src_xpath='//div[@class="text"]//img'
                                       )

        announcement_title = temp['announcement_title']
        release_date = temp['release_date'].strip()
        entity_name = temp['entity_name']
        items = {}
        if entity_name:
            md5_value = hash_md5(release_date + entity_name + announcement_title)
            items['md5_value'] = md5_value
            items['release_date'] = release_date
            items['entity_name'] = entity_name
            items['announcement_title'] = announcement_title
            items['announcement_url'] = temp['announcement_url']
            items['content'] = html_node_code
            items['source'] = '湖南省市场监督管理局'
            self.log_info(items)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
