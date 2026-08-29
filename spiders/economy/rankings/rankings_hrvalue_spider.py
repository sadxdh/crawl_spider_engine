"""HR价值网榜单爬虫 → rankings_information"""
import hashlib, scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *
import time


class RankingsHrvalueSpider(BaseSpider):
    name = 'economy_rankings_hrvalue'
    data_table = 'rankings_information'
    allowed_domains = ['www.hrvalue.com.cn']
    custom_settings = {'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1}
    proxy_type = 'long_proxy'
    dedup_fields = ['md5_value']
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Referer': 'https://www.hrvalue.com.cn/bangdan/?page=2',
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            if page == 1:
                url = f'https://www.hrvalue.com.cn/bangdan/?page=1'
            else:
                url = f'https://www.hrvalue.com.cn/bangdan/?page={page}'
            yield scrapy.Request(
                url=url,
                method='GET',
                headers=self.headers,
                callback=self.parse_list,
                errback=self.errback,
                dont_filter=True,
                cb_kwargs={'url': url},
            )

    def parse_list(self, response, url):
        etree_html = etree.HTML(response.text)
        datas = etree_html.xpath('//div[@class="ins-bangdan-list"]/ul/li')
        for data in datas:
            url_list = data.xpath('./a/@href')[0]
            url_data = urljoin(url, url_list)
            title = data.xpath('./a/@title')[0]
            yield scrapy.Request(
                url=url_data,
                method='GET',
                headers=self.headers,
                callback=self.parse_item,
                errback=self.errback,
                dont_filter=True,
                cb_kwargs={'title': title, 'url_data': url_data},
            )

    def parse_item(self, response, title, url_data):
        etree_html = etree.HTML(response.text)
        items = etree_html.xpath('//div[@class="bangdan-list"]/ul/li')
        for item in items:
            ranking = item.xpath('./div[@class="bd-nb"]/em/text()')[0]
            name = item.xpath('./div[@class="bd-nm"]/text()')[0]
            img = urljoin(url_data, item.xpath('./div[@class="bd-img"]/img/@src')[0])
            img_name = name + img[-4:]
            region = item.xpath('./div[@class="bd-dq"]/text()')[0].replace('·', '')

            items = {}
            md5_value = hash_md5(title + name)
            items['md5_value'] = md5_value
            items['url'] = url_data
            items['ranking'] = ranking
            items['rankings_title'] = title
            items['region'] = region
            items['rankings_name'] = name
            items['source'] = 'hrValue'
            items['announcement_title'] = img_name
            items['announcement_url'] = img
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
