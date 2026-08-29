import hashlib, scrapy
import math
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class CompanyReportEastmoneySpider(BaseSpider):
    name = 'company_report_eastmoney_spider'
    data_table = 'entity_announcement'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://xinsanban.eastmoney.com/Article/NoticeList',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Microsoft Edge";v="128"',
    }
    base_url = 'https://xinsanban.eastmoney.com/api/gg/list'
    detail_url = 'https://xinsanban.eastmoney.com/Article/NoticeContent?id={}'
    announcement_type = {
        '财务公告': 1,
        '融资公告': 2,
        '重大事项': 3,
        '资产重组': 4,
        '风险提示': 5,
        '持股变动': 6,
        '信息变更': 7
    }

    @staticmethod
    def generate_params(type_code, start_date, end_date, page):
        params = {
            'page_index': page,
            'type': type_code,
            'begin': start_date,
            'end': end_date,
            'securitycodes': '',
            'content': '',
            'sortRule': '1',
        }
        return params

    def start_requests(self):
        if self.end_page < 0:
            year_list = generate_every_year_date('2000-01-01', f'{return_yesterday().year}-12-31')
        else:
            year_list = generate_every_month_date(f'{return_yesterday().year}-01-01', f'{return_yesterday().year}-12-31')
        for type_name, type_code in self.announcement_type.items():
            for year_time in year_list:
                start_date, end_date = year_time
                params = self.generate_params(type_code, start_date, end_date, 1)
                separator = '&' if '?' in self.base_url else '?'
                request_url = f'{self.base_url}{separator}{urlencode(params)}'
                yield scrapy.Request(
                    url=request_url,
                    method='GET',
                    headers=self.headers,
                    callback=self.parse_page_num,
                    dont_filter=True,
                    cb_kwargs={'type_code': type_code, 'start_date': start_date, 'end_date': end_date, 'type_name': type_name}
                )

    def parse_page_num(self, response, type_code, start_date, end_date, type_name):
        if response:
            total = response.json()['total']
            page_num = math.ceil(int(total) / 20)
            page_count = page_num if self.end_page < 0 else self.end_page
            for page in range(self.start_page, int(page_count)+1):
                params = self.generate_params(type_code, start_date, end_date, page)
                separator = '&' if '?' in self.base_url else '?'
                request_url = f'{self.base_url}{separator}{urlencode(params)}'
                yield scrapy.Request(
                    url=request_url,
                    method='GET',
                    headers=self.headers,
                    callback=self.parse_list,
                    dont_filter=True,
                    cb_kwargs={'type_name': type_name}
                )

    def parse_list(self, response, type_name):
        result = response.json()['result']
        for data in result:
            art_code = data['art_code']
            publish_time = data['notice_date']
            announcement_title = data['title']

            codes = data['codes'][0]
            security_code = codes['stock_code']
            security_short = codes['short_name']

            md5_value = hash_md5(str(publish_time) + announcement_title + security_code)

            items = {}
            items['publish_time'] = publish_time
            items['announcement_title'] = announcement_title
            items['announcement_type'] = type_name
            items['security_code'] = security_code
            items['security_short'] = security_short
            items['security_type'] = '新三板'
            items['source'] = '东方财富网'
            items['md5_value'] = md5_value
            # insert_data(table='entity_announcement', data=item)

            detail_url = self.detail_url.format(art_code)
            yield scrapy.Request(
                url=detail_url,
                method='GET',
                headers=self.headers,
                cb_kwargs={'items': items},
                callback=self.parse_detail
            )

    def parse_detail(self, response, items):
        result = etree.HTML(response.text)
        announcement_url = result.xpath('//a[@class="lookmore"]/@href')[0]
        items['announcement_url'] = announcement_url
        yield items


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')