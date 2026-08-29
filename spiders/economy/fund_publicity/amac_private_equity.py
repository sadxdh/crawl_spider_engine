"""AMAC → securities_private_equity_fund
旧项目参照: data_crawl_server securities_private_equity.py
"""
import hashlib, random, time, scrapy
from utils.amac_fetch import amac_post
from spiders.base_spider import BaseSpider
from utils.tools import *

_LIST_URL = 'https://gs.amac.org.cn/amac-infodisc/api/pof/subfund?rand={r}&page={p}&size=20'


class _Spider(BaseSpider):
    name = 'amac_private_equity'
    data_table = 'securities_private_equity_fund'
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
        # "Referer": "https://gs.amac.org.cn/amac-infodisc/res/cancelled/manager/index.html",
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
        url = f'https://gs.amac.org.cn/amac-infodisc/api/pof/subfund?rand={random.random()}&page=0&size=20'
        yield scrapy.Request(
            url=url,
            method="POST",
            headers=self.headers,
            body=json.dumps({}, separators=(",", ":")),
            callback=self.parse_total_pages,
            dont_filter=True,
        )

    def parse_total_pages(self, response):
        if int(self.end_page) < 0:
            count_page = response.json()['totalPages']
            pages = [page for page in range(int(self.start_page) - 1, int(count_page))]
        else:
            pages = [page for page in range(int(self.start_page) - 1, int(self.end_page))]
        for page in pages:
            details_url = f'https://gs.amac.org.cn/amac-infodisc/api/pof/subfund?rand={random.random()}&page={page}&size=20'
            yield scrapy.Request(
                url=details_url,
                method="POST",
                headers=self.headers,
                body=json.dumps({}, separators=(",", ":")),
                callback=self.parse_urls,
                dont_filter=True,
                cb_kwargs={'details_url': details_url}
            )

    def parse_urls(self, response, details_url):
        response = response.json()
        for content_data in reversed(response['content']):
            product_name = content_data['productName']
            product_code = content_data['productCode']
            administrator_name = content_data['mgrName']
            establish_date = time.strftime("%Y-%m-%d", time.localtime(content_data['foundDate'] / 1000))
            filing_date = time.strftime("%Y-%m-%d", time.localtime(content_data['registeredDate'] / 1000))
            fund_type = content_data['fundType']
            organizational_form = content_data['orgForm']
            operation_status = content_data['fundStatus']
            whether_trusteeship = content_data['tuoGuan']
            whether_name = content_data['trustee']
            url = f"https://gs.amac.org.cn/amac-infodisc/res/pof/subfund/{content_data['id']}.html"

            md5_value = hash_md5(product_name + product_code)
            items = {}
            items['md5_value'] = md5_value
            items['product_name'] = product_name
            items['product_code'] = product_code
            items['administrator_name'] = administrator_name
            items['establish_date'] = establish_date
            items['filing_date'] = filing_date
            items['fund_type'] = fund_type
            items['organizational_form'] = organizational_form
            items['operation_status'] = operation_status
            items['whether_trusteeship'] = whether_trusteeship
            items['whether_name'] = whether_name
            items['fund_url'] = url
            yield items

    def errback(self, f):
        self.log_error(f'请求失败: {f.request.url}')

