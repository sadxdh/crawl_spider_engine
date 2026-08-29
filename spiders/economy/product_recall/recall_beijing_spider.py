"""产品召回-北京市监局，来源：https://scjgj.beijing.gov.cn/zwxx/gs/zhxxzx → product_recall"""
import re, scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *
_C = lambda v: (v[0] if isinstance(v, list) and v else v or '').strip()


class BeijingRecallSpider(BaseSpider):
    name = 'economy_recall_beijing'
    data_table = 'product_recall'
    allowed_domains = ['scjgj.beijing.gov.cn']
    proxy_type = 'long_proxy'
    dedup_fields = ['md5_value']
    custom_settings = {'CONCURRENT_REQUESTS': 8, 'DOWNLOAD_DELAY': 0.3}
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;'
                  'q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://scjgj.beijing.gov.cn/zwxx/gs/zhxxzx/index_1.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0',
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            if page == 1:
                url = 'https://scjgj.beijing.gov.cn/zwxx/gs/zhxxzx/index.html'
            else:
                url = f'https://scjgj.beijing.gov.cn/zwxx/gs/zhxxzx/index_{page - 1}.html'
            yield scrapy.Request(
                url,
                headers=self.headers,
                callback=self.parse_list,
                errback=self.errback
            )

    def parse_list(self, response):
        result = etree.HTML(response.text)
        rows = result.xpath('//div[@class="public_list_team"]/ul/li')
        for row in rows:
            announcement_title = row.xpath('./a/@title')[0]
            href = row.xpath('./a/@href')
            announcement_url = urljoin(response.url, href[0])
            release_date = row.xpath('./span/text()')[0]

            entity_name = match_text(announcement_title, pattern=r'(.*?公司|.*?厂|.*?店).*召回')
            entity_name = entity_name.split('】')[1] if entity_name and '】' in entity_name else entity_name

            temp = {'announcement_title': announcement_title, 'announcement_url': announcement_url,
                    'release_date': release_date, 'entity_name': entity_name}
            yield scrapy.Request(
                url=announcement_url,
                headers=self.headers,
                callback=self.parse_detail,
                errback=self.errback,
                meta=temp
            )

    def parse_detail(self, response):
        if response:
            html_node_code = get_node_html(response,
                                           content_xpath='//div[@id="div_zhengwen"]/div',
                                           replace_src_xpath='//p/img')
        else:
            html_node_code = None

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
            items['source'] = '北京市市场监督管理局'
            self.log_info(items)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
