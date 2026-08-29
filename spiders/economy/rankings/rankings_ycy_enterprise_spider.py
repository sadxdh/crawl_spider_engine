"""胡润榜单爬虫 → rankings_information"""
import hashlib, scrapy;
from spiders.base_spider import BaseSpider
from utils.tools import *
import time
from urllib.parse import parse_qs, urlencode


# 网站改版了
class RankingsYcyEnterpriseSpider(BaseSpider):
    name = 'economy_rankings_ycy_enterprise'
    data_table = 'rankings_information'
    allowed_domains = ['api-report.dichan.com']
    custom_settings = {'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1}
    proxy_type = 'long_proxy'
    dedup_fields = ['md5_value']
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Referer': 'https://www.jiqizhixin.com/articles/2020-09-29-9',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Priority': 'u=0, i',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }

    def start_requests(self):
        url = 'https://api-report.dichan.com/api/index'
        yield scrapy.Request(
            url=url,
            body=b"",
            method='POST',
            headers=self.headers,
            callback=self.parse_list,
            errback=self.errback,
            dont_filter=True,
        )

    def parse_list(self, response):
        datas = response.json()
        data = datas['data']['category']
        years = datas['data']['year']
        for year in years:
            year = year['year']
            for item in data:
                id = item['id']
                title = item['title']
                json_data = {
                    'city': '全国',
                    'year': str(year),
                    'category': id,
                }
                self.url = 'https://api-report.dichan.com/api/index'
                yield scrapy.FormRequest(
                    url=self.url,
                    formdata=json_data,
                    method='POST',
                    headers=self.headers,
                    callback=self.parse_url,
                    errback=self.errback,
                    dont_filter=True,
                    cb_kwargs={'title1': title, 'json_data': json_data}
                )

    def parse_url(self, response, title1, json_data):
        data1 = response.json()
        title1 = f"{json_data['year']}优采云{title1}"
        data = data1['data']['list'].get('child', [])
        if data:
            for items in data:
                if items['data']:
                    title = f"{title1}-{items['title']}供应链榜单"
                    for item in items['data']:
                        data_data = self.parse_item(item, title)
                        yield data_data
                else:
                    data = data1['data']['list']['data']
                    title2 = data1['data']['list']['title']
                    title = f'{title1}-{title2}供应链榜单'
                    for item in data:
                        data_data = self.parse_item(item, title)
                        yield data_data
        else:
            data = data1['data']['list']['data']
            title2 = data1['data']['list']['title']
            title = f'{title1}-{title2}供应链榜单'
            for item in data:
                data_data = self.parse_item(item, title)
                yield data_data

    def parse_item(self, item, title):
        ranking = item['ROW_NUMBER']
        company = item['company']
        if company:
            CompanyName = company['CompanyName']
            logo = company['logo'] if company['logo'] else None
        else:
            CompanyName = item['company_name']
            logo = None
        announce = CompanyName + logo[-4:] if logo else None
        md5_value = hash_md5(title + CompanyName)
        items = {}
        items['md5_value'] = md5_value
        items['url'] = self.url
        items['rankings_title'] = title
        items['rankings_name'] = CompanyName
        items['ranking'] = ranking
        items['source'] = '优采云'
        items['announcement_title'] = announce
        items['announcement_url'] = logo
        return items


    def errback(self, failure): self.log_error(f'请求失败: {failure.request.url} — {failure.value}')