"""品牌联盟榜单 → rankings_information
参照旧项目 brand_alliance.py: topbrand500.com
"""
import hashlib, scrapy
from lxml import etree

from spiders.base_spider import BaseSpider
from utils.tools import *


class RankingsBrandEnterpriseSpider(BaseSpider):
    name = 'economy_rankings_brand_enterprise'
    data_table = 'rankings_information'
    allowed_domains = ['www.topbrand500.com']
    default_end_page = 1
    proxy_type = 'long_proxy'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2,
        'DOWNLOAD_DELAY': 1,
    }
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;'
                  'q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'referer': 'https://www.topbrand500.com/ranking.html?page=1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    }

    def data_replace(self, data):
        if data:
            return data[0].strip()
        else:
            return ''

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            get_type_url = f'https://www.topbrand500.com/ranking-enterprise.html?page={page}'
            yield scrapy.Request(
                url=get_type_url,
                headers=self.headers,
                callback=self.parse_urls,
                errback=self.errback
            )

    def parse_urls(self, response):
        type_xpath = etree.HTML(response.body)
        div_data_list = type_xpath.xpath('//div[@class="items mb"]/div')

        for div_data in div_data_list:
            get_detail_url = div_data.xpath('./div[@class="box"]/a/@href')[0]
            rankings_title = self.data_replace(div_data.xpath('./@title'))
            if "金谱奖" not in rankings_title:
                yield scrapy.Request(
                    url=get_detail_url,
                    headers=self.headers,
                    errback=self.errback,
                    callback=self.parse_list,
                    cb_kwargs={'get_detail_url': get_detail_url, 'rankings_title': rankings_title}
                )

    def parse_list(self, response, get_detail_url, rankings_title):
        detail_xpath = etree.HTML(response.body)
        tr_data_list = detail_xpath.xpath('//div[@class="table"]/table/tbody/tr')
        # 创新版多余表单判断
        tr_data_list = tr_data_list[1:] if any(
            term in rankings_title for term in ['创新', '广东']) else tr_data_list
        for tr_data in tr_data_list:
            ranking = self.data_replace(tr_data.xpath('./td[1]//text()'))  # 排名
            rankings_name = self.data_replace(tr_data.xpath('./td[2]//text()'))  # 名称
            industry = self.data_replace(tr_data.xpath('./td[3]//text()'))  # 行业
            region = self.data_replace(tr_data.xpath('./td[4]//text()'))  # 地区
            brand_value = self.data_replace(tr_data.xpath('./td[5]//text()'))  # 品牌价值
            innovation_index = ''  # 创新指数
            huapu_category = ''  # 华谱类别

            items = {}
            # 正常数据
            items['source'] = '品牌联盟'
            items['rankings_title'] = rankings_title
            items['url'] = get_detail_url
            # 易错位数据
            items['brand_value'] = brand_value
            items['industry'] = industry
            items['ranking'] = ranking
            items['rankings_name'] = rankings_name
            items['huapu_category'] = huapu_category
            items['region'] = region
            items['innovation_index'] = innovation_index
            if '创新' in rankings_title:
                # 创新版页面从表单开始比其他页面多了一行需要剔除,已再元素定位列表循环加上判断
                items['region'] = ""
                items['innovation_index'] = region
            elif "华谱" in rankings_title:
                # 数据错位调整数据位置
                if items['rankings_title'] == "2023中国品牌节华谱奖":
                    items['ranking'] = ranking
                    items['rankings_name'] = rankings_name
                    items['industry'] = ''
                else:
                    items['ranking'] = ''
                    items['rankings_name'] = ranking
                    items['huapu_category'] = rankings_name
                    items['industry'] = ''
            elif "广东" in rankings_title:
                items['brand_value'] = industry
                items['industry'] = region
                items['region'] = ''
            md5_value = hash_md5(rankings_title + rankings_name)
            items['md5_value'] = md5_value
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
