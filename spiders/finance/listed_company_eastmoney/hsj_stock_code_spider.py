import hashlib, scrapy
import math
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.finance.listed_company_eastmoney.fs_key_value import fs_value
from utils.mysql_tools import select_data, update_set
from utils.tools import *
from utils.time_kit import *

class HsjStockCodeSpider(BaseSpider):
    name = 'hsj_stock_code'
    data_table = 'stock_hsj'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 4, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        },
        # 'COOKIES_ENABLED': True  # 使用cookie字段必须得要
    }
    proxy_type = 'long_proxy'

    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Referer": "https://quote.eastmoney.com/center/gridlist.html",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": "\"Not;A=Brand\";v=\"8\", \"Chromium\";v=\"150\", \"Google Chrome\";v=\"150\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    md5_value_list = set()

    def start_requests(self):
        url = "https://quote.eastmoney.com/center/api/sidemenu_new.json"
        yield scrapy.Request(
            url=url,
            headers=self.headers,
            callback=self.get_stock_type
        )

    def get_stock_type(self, response):
        json_data = response.json()
        for sidemenu in json_data['sidemenu']:
            if sidemenu['title'] == "沪深京个股":
                for stock in sidemenu['sub']:
                    if stock['title'] == "两网及退市":
                        continue
                    fs = fs_value[stock['path'].replace('#', '')]['fs']
                    url = "https://push2.eastmoney.com/webguest/api/qt/clist/get"
                    params = {
                        "np": "1",
                        "fltt": "1",
                        "invt": "2",
                        "cb": "",
                        "fs": fs,
                        "fields": "f12,f13",
                        "fid": "f12",
                        "pn": "1",
                        "pz": "20",
                        "po": "1",
                        "dect": "1",
                        "ut": "",
                        "wbp2u": "",
                        "_": ""
                    }
                    yield scrapy.Request(
                        url=f"{url}?{urlencode(params)}",
                        headers=self.headers,
                        callback=self.get_all_page,
                        errback=self.errback,
                        cb_kwargs={'fs': fs},
                        dont_filter=True
                    )

    def get_all_page(self, response, fs):
        json_data = json.loads(response.text)
        all_number = json_data['data']['total']
        self.log_info(f"{fs}总共有{all_number}条数据")
        last_page = math.ceil(int(all_number) / 100)
        self.log_info(f"总共有{last_page}")
        for page in range(int(self.start_page), int(last_page) + 1):
            self.log_info(f"正在采集第{page}页")
            url = "https://push2.eastmoney.com/webguest/api/qt/clist/get"
            params = {
                "np": "1",
                "fltt": "1",
                "invt": "2",
                "cb": "",
                "fs": fs,
                "fields": "f12,f13",
                "fid": "f12",
                "pn": str(page),
                "pz": "100",
                "po": "1",
                "dect": "1",
                "ut": "",
                "wbp2u": "",
                "_": ""
            }
            yield scrapy.Request(
                url=f"{url}?{urlencode(params)}",
                headers=self.headers,
                callback=self.parse_list,
                dont_filter=True
            )

    def parse_list(self, response):
        json_data = json.loads(response.text)
        for data in json_data['data'].get('diff', []):
            md5_value = hash_md5(data['f12'])
            self.md5_value_list.add(md5_value)
            stock_code = data['f12']
            area = data['f13']
            status = 1

            main_item = {}
            main_item['md5_value'] = md5_value
            main_item['status'] = status
            main_item['area'] = area
            main_item['stock_code'] = stock_code
            yield main_item


    def closed(self, reason):
        """爬虫所有请求和入库操作完成后执行。"""
        self.log_info(f"爬虫结束，原因：{reason}；开始查询 表：{self.data_table} 的数据")
        code_md5_list = select_data(
            table='stock_hsj', data=['md5_value'],
        )
        for code_md5 in code_md5_list:
            code_md5_value = code_md5['md5_value']
            if code_md5_value not in self.md5_value_list:
                main_item = {
                    'md5_value': code_md5_value,
                    'status': 0
                }
                update_set(table='stock_hsj', data=main_item)

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')