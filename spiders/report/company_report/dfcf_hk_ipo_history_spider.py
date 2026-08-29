import hashlib, scrapy
import math
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *
from utils.mysql_tools import select_data

class DfcfHkIpoHistorySpider(BaseSpider):
    name = 'dfcf_hk_ipo_history_spider'
    data_table = 'ipo_pdf'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "referer": "https://data.eastmoney.com/notices/stock/08271.html",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
    }
    base_url = "https://np-anotice-stock.eastmoney.com/api/security/ann"

    @staticmethod
    def generate_params(stock_code, page):
        params = {
            "cb": "",
            "sr": "-1",
            "page_size": "50",
            "page_index": f"{page}",
            "ann_type": "H",
            "client_source": "web",
            "stock_list": f"{stock_code}",
            "f_node": "0"
        }
        return params

    def start_requests(self):
        end_date = '2025-07-01'
        code_list = select_data(table='stock_hk', data=['entity_id'], condition=f'id >0 limit {self.end_page}')
        for code in code_list:
            stock_code = code['entity_id']
            params = self.generate_params(stock_code, page=1)
            separator = "&" if "?" in self.base_url else "?"
            request_url = f"{self.base_url}{separator}{urlencode(params)}"
            yield scrapy.Request(
                url=request_url,
                method="GET",
                headers=self.headers,
                callback=self.get_list,
                dont_filter=True,
                cb_kwargs={'end_date': end_date, 'data': code}
            )

    def get_page(self, response):
        if response:
            result = response.json()['data']
            if result:
                page_size = result['page_size']
                total_hits = result['total_hits']
                total_count = math.ceil(total_hits / page_size)
                return total_count
        return 20

    def get_list(self, response, end_date, data):
        total_page = self.get_page(response)
        for page in range(1, total_page + 1):
            stock_code = data['entity_id']
            params = self.generate_params(stock_code, page)
            separator = "&" if "?" in self.base_url else "?"
            request_url = f"{self.base_url}{separator}{urlencode(params)}"
            yield scrapy.Request(
                url=request_url,
                method="GET",
                headers=self.headers,
                callback=self.parse_list,
                dont_filter=True,
                cb_kwargs={'end_date': end_date}
            )

    def parse_list(self, response, end_date):
        result = response.json()
        result = result['data']
        if result:
            data_list = result['list']

            for data in data_list:
                notice_date = data['notice_date']
                if end_date and end_date > notice_date:

                    art_code = data['art_code']
                    codes = data['codes'][0]
                    code = codes['stock_code']
                    code_name = codes['short_name']
                    column_name = data['columns'][0]['column_name']
                    ipo_type = '港股公告'
                    source_url = f'https://data.eastmoney.com/notices/detail/{code}/{art_code}.html'
                    ann_title = data['title']
                    pdf_url = f'https://pdf.dfcfw.com/pdf/H2_{art_code}_1.pdf'

                    md5_value = hash_md5(pdf_url)

                    items = {}
                    items['md5_value'] = md5_value
                    items['code'] = code
                    items['code_name'] = code_name
                    items['column_name'] = column_name
                    items['ipo_type'] = ipo_type
                    items['source_url'] = source_url
                    items['announcement_title'] = ann_title
                    items['announcement_url'] = pdf_url
                    items['release_time'] = notice_date
                    # insert_data(table='ipo_pdf', data=item)
                    yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')