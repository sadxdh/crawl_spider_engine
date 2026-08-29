"""品牌联盟个人榜单 → personal_rankings
参照旧项目 data_crawl_server brand_alliance.py: topbrand500.com 个人榜
"""
import hashlib, scrapy
from lxml import etree
from urllib.parse import urljoin
from spiders.base_spider import BaseSpider
from utils.tools import *


class RankingsBrandPersonSpider(BaseSpider):
    name = 'economy_rankings_brand_person'
    data_table = 'personal_rankings'
    proxy_type = 'long_proxy'
    dedup_fields = ['md5_value']
    allowed_domains = ['www.topbrand500.com']
    default_end_page = 1

    custom_settings = {'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1}
    get_type_headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
                  ',application/signed-exchange;v=b3;q=0.7',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'zh-CN,zh;q=0.9',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127'
                      '.0.0.0 Safari/537.36',
    }

    def data_replace(slef, data):
        if data:
            return data[0].strip()
        else:
            return ''

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            get_type_url = f'https://www.topbrand500.com/ranking-personage.html?page={page}'
            yield scrapy.Request(
                url=get_type_url,
                headers=self.get_type_headers,
                callback=self._parse_list,
                errback=self.errback
            )

    def _parse_list(self, response):
        type_xpath = etree.HTML(response.body)
        div_data_list = type_xpath.xpath('//div[@class="items mb"]/div')
        for div_data in div_data_list:
            if self.data_replace(div_data.xpath('./@title')) in ['2024品牌女性喜爱的品牌50强', '2024网红达人品牌女性500强']:
                continue  # 跳过不需要的榜单
            get_detail_url = div_data.xpath('./div[@class="box"]/a/@href')[0]
            rankings_title = self.data_replace(div_data.xpath('./@title'))
            yield scrapy.Request(
                url=get_detail_url,
                headers=self.get_type_headers,
                callback=self._parse_detail,
                errback=self.errback,
                cb_kwargs={'get_detail_url': get_detail_url, 'rankings_title': rankings_title, 'div_data': div_data}
            )

    def _parse_detail(self, response, get_detail_url, rankings_title, div_data):
        detail_xpath = etree.HTML(response.body)
        tr_data_list = detail_xpath.xpath('//div[@class="table"]/table/tbody/tr')
        for tr_data in tr_data_list:
            ranking = self.data_replace(tr_data.xpath('./td[1]//text()'))
            if ranking is not None and ranking.isdigit() and 1 <= int(ranking) <= 500:
                name = self.data_replace(tr_data.xpath('./td[2]/text()'))
                md5_value = hash_md5(rankings_title + name)
                items = {}
                items['md5_value'] = md5_value
                items['ranking'] = ranking
                items['name'] = name
                items['rankings_title'] = rankings_title
                if '世界品牌人物' in rankings_title:
                    position = self.data_replace(tr_data.xpath('./td[4]/text()'))
                    items['position'] = position
                    en_name = self.data_replace(tr_data.xpath('./td[3]/text()'))
                    items['en_name'] = en_name
                    yield items
                else:
                    position = self.data_replace(tr_data.xpath('./td[3]/text()'))
                    items['position'] = position
                    yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
