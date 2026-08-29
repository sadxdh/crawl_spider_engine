"""产品召回-山东省监局，来源：https://amr.shandong.gov.cn/col/col94098 → product_recall"""
import hashlib, re, scrapy;
from lxml import etree;
from spiders.base_spider import BaseSpider
from utils.tools import *

_C = lambda v: (v[0] if isinstance(v, list) and v else v or '').strip()


class ShandongRecallSpider(BaseSpider):
    name = 'economy_recall_shandong'
    data_table = 'product_recall'
    allowed_domains = ['amr.shandong.gov.cn']
    proxy_type = 'long_proxy'
    dedup_fields = ['md5_value']
    custom_settings = {'CONCURRENT_REQUESTS': 8, 'DOWNLOAD_DELAY': 0.3}
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;'
                  'q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'http://amr.shandong.gov.cn/col/col76511/index.html?number=&uid=445106&pageNum=1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0',
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            url = f"http://amr.shandong.gov.cn/module/web/jpage/dataproxy.jsp?startrecord={page * 20 + 1}&endrecord={(page + 1) * 20 + 1}&perpage=20&unitid=445106&webid=67&path=http://amr.shandong.gov.cn/&webname=%E5%B1%B1%E4%B8%9C%E7%9C%81%E5%B8%82%E5%9C%BA%E7%9B%91%E7%9D%A3%E7%AE%A1%E7%90%86%E5%B1%80&col=1&columnid=76511&sourceContentType=1&permissiontype=0"
            yield scrapy.Request(
                url=url,
                headers=self.headers,
                callback=self.parse_list,
                errback=self.errback
            )

    def parse_list(self, response):
        result = response.text.replace('\n', '')
        result = re.findall(r'<record><!\[CDATA\[(.*?)]]></record>', result)
        for res in result:
            row = etree.HTML(res)
            announcement_title = row.xpath('//li/a/@title')[0]
            href = row.xpath('//li/a/@href')
            announcement_url = urljoin(response.url, href[0])
            release_date = row.xpath('//li/span[not(@class)]/text()')[0]

            entity_name = match_text(announcement_title, pattern=r'(.*?公司|.*?厂|.*?店).*召回')
            entity_name = entity_name.split('】')[1] if entity_name and '】' in entity_name else entity_name

            temp = {'announcement_title': announcement_title, 'announcement_url': announcement_url,
                    'release_date': release_date, 'entity_name': entity_name}
            yield scrapy.Request(
                url=announcement_url,
                headers=self.headers,
                callback=self.parse_detail,
                errback=self.errback,
                cb_kwargs={'parms': temp}
            )

    def parse_detail(self, response, parms):
        html_node_code = get_node_html(response,
                                       content_xpath='//div[@class="text_content"]',
                                       replace_src_xpath='//p//img')
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
            items['content'] = html_node_code
            items['source'] = '山东省市场监督管理局'
            self.logger.info(items)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
