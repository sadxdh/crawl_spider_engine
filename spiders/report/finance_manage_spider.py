"""金融管理局公告爬虫 → admin_permit
旧项目参照: data_crawl_server shandong_finance_spider.py
数据来源: dfjrjgj.shandong.gov.cn
"""
import hashlib, scrapy
from lxml import etree
from urllib.parse import urljoin, urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *


class FinanceManageSpider(BaseSpider):
    name = 'report_finance_manage'
    data_table = 'admin_permit'
    dedup_fields = ['md5_value']
    allowed_domains = ['dfjrjgj.shandong.gov.cn']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,'
                  'image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/126.0.0.0 Safari/537.36',
    }

    base_url = 'http://dfjrjgj.shandong.gov.cn/channels/ch05651/index.shtml'

    @staticmethod
    def generate_params(page):
        return {'page': page}

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            params = self.generate_params(page)
            url = f"{self.base_url}?{urlencode(params)}"
            yield scrapy.Request(
                url=url,
                method="GET",
                headers=self.headers,
                callback=self.parse_list
            )

    def parse_list(self, response):
        response = response.text.encode(response.encoding).decode('utf-8')
        result = etree.HTML(response)
        rows = xpath_parse(result, '//div[@class="wei"]/ul/li', return_list=True)
        for row in rows[:50]:
            title = xpath_parse(row, './a/text()')
            url = xpath_parse(row, './a/@href')
            release_date = xpath_parse(row, './span/text()')
            temp = {'title': title, 'url': url, 'release_date': release_date}
            yield scrapy.Request(
                url=url,
                method="GET",
                headers=self.headers,
                callback=self.parse_detail,
                cb_kwargs={'data': temp}
            )

    def parse_detail(self, response, data):
        response = response.text.encode(response.encoding).decode('utf-8')
        html_str = html_to_str(response, '//div[contains(@class,"wz_zoom")]')
        title = data['title']
        url = data['url']
        release_date = data['release_date']
        web_name = '山东省地方金融管理局'
        md5_value = hash_md5(title+str(release_date)+web_name)

        items = {}
        items['title'] = title
        items['url'] = url
        items['release_date'] = release_date
        items['content'] = html_str
        items['web_name'] = web_name
        items['md5_value'] = md5_value
        # insert_data('admin_permit', items)
        yield items

        yield from self.extract_attachment(response, md5_value)
        # for attach in attach_list:
        #     attach_title = attach['attach_title']
        #     attach_url = attach['attach_url']
        #     temp = {'attach_title': attach_title, 'attach_url': attach_url, 'md5_value': md5_value}
        #     yield temp

    @staticmethod
    def extract_attachment(response, md5_value):
        result = etree.HTML(response)
        rows = xpath_parse(result, '//div[contains(text(), "附件")]/a', return_list=True)
        if rows is not None:
            for row in rows:
                attach_title = xpath_parse(row, './text()')
                href = xpath_parse(row, './@href')
                attach_url = urljoin(response.url, href)
                items = {}
                items['attach_title'] = attach_title
                items['attach_url'] = attach_url
                items['md5_value'] = md5_value
                yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
