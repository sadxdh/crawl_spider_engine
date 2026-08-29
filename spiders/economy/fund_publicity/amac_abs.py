"""AMAC 资产支持专项计划 → asset_backed_plan"""
import hashlib
import random
import time

import scrapy
from utils.amac_fetch import amac_post
from spiders.base_spider import BaseSpider
from utils.tools import *

_LIST_URL = 'https://gs.amac.org.cn/amac-infodisc/api/fund/abs?rand={r}&page={p}&size=20'



class AbsSpider(BaseSpider):
    name = 'amac_abs'
    data_table = 'asset_backed_plan'
    allowed_domains = ['gs.amac.org.cn']
    default_end_page = 2
    custom_settings = {
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'
    dedup_fields = ['md5_value']
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Origin": "https://gs.amac.org.cn",
        "Referer": "https://gs.amac.org.cn/amac-infodisc/res/fund/abs/index.html",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    def start_requests(self):
        url = f"https://gs.amac.org.cn/amac-infodisc/api/fund/abs?rand={random.random()}&pageNo=0&pageSize=20"
        yield scrapy.Request(
            url=url,
            method="POST",
            headers=self.headers,
            body=json.dumps({}, separators=(",", ":")),
            callback=self.parse_total_pages,
            dont_filter=True,
        )

    def parse_total_pages(self, response):
        count_page = response.json().get('totalPages')
        if int(self.end_page) < 0:
            pages = [page for page in range(int(self.start_page) - 1, int(count_page))]
        else:
            pages = [page for page in range(int(self.start_page) - 1, int(self.end_page) - 1)]
        for page in pages:
            details_url = f'https://gs.amac.org.cn/amac-infodisc/api/fund/abs?rand={random.random()}&pageNo={page}&pageSize=20'
            yield scrapy.Request(
                url=details_url,
                method="POST",
                headers=self.headers,
                body=json.dumps({}, separators=(",", ":")),
                callback=self.parse_urls,
                dont_filter=True,
                errback=self.errback,
                cb_kwargs={"details_url": details_url},
            )

    def parse_urls(self, response, details_url):
        def convert_timestamp(timestamp, divisor=1000, fallback_divisor=100000):
            try:
                return time.strftime("%Y-%m-%d", time.localtime(timestamp / divisor))
            except (ValueError, OverflowError, OSError):
                try:
                    # 如果失败，尝试使用备用除数
                    return time.strftime("%Y-%m-%d", time.localtime(timestamp / fallback_divisor))
                except (ValueError, OverflowError, OSError):
                    return "Invalid Timestamp"

        response = response.json()
        for content_data in reversed(response['content']):
            product_code = content_data['productCode']
            special_plan_name = content_data['productName']
            administrator_name = content_data['orgName']
            whether_name = content_data['trustee']
            establish_date = convert_timestamp(content_data['fundFoundDate'])
            expire_date = convert_timestamp(content_data['fundDueDate'])
            adopt_date = convert_timestamp(content_data['registeredDate'])

            md5_value = hash_md5(special_plan_name + product_code)
            items = {}
            items['md5_value'] = md5_value
            items['product_code'] = product_code
            items['special_plan_name'] = special_plan_name
            items['administrator_name'] = administrator_name
            items['whether_name'] = whether_name
            items['establish_date'] = establish_date
            items['expire_date'] = expire_date
            items['adopt_date'] = adopt_date
            items['fund_url'] = details_url
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
