import hashlib, scrapy
import math
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.finance.listed_company_eastmoney.fs_key_value import fs_value
from utils.mysql_tools import select_data
from utils.tools import *
from utils.time_kit import *


# https://quote.eastmoney.com/center/gridlist.html#hs_a_board
# 东方财富网-沪深京个股-题材详情
class SubjectMatterEastmoneySpider(BaseSpider):
    name = 'subject_matter_eastmoney'
    data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        },
        #'COOKIES_ENABLED': True  # 使用cookie字段必须得要
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

    def start_requests(self):
        code_list = select_data(
            table='stock_hsj', data=['stock_code', 'status', 'area'],
            suffix='GROUP BY stock_code ORDER BY stock_code'
        )
        for code in code_list:
            stock_code = code['stock_code']
            status = code['status']
            f13 = code['area']
            if status == 1 or status == '1':
                logger.warning(f"stock_code:{stock_code}")
                old_url = f"https://quote.eastmoney.com/unify/r/{f13}.{stock_code}"
                yield scrapy.Request(
                    url=old_url,
                    method="GET",
                    headers=self.headers,
                    callback=self.parse_details_url,
                    cb_kwargs={'f13': f13}
                )

    def parse_details_url(self, response, f13):
        new_url = response.url
        url_key = new_url.replace('//quote.eastmoney.com/', '').replace('/', '').replace('.html', '').replace(
            'https:', '').upper()
        prefix, code = re.match(r"([A-Za-z]+)(\d+)", url_key).groups()
        if f13 == 1 or f13 == "1":
            prefix = "SH"
        details_url = f"https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code={prefix}{code}&color=b#/hxtc"
        yield from self.get_details({'detail_url': details_url, 'code': code, 'prefix': prefix})

    def get_details(self, data):
        code = data['code']
        prefix = data['prefix']
        url = "https://datacenter.eastmoney.com/securities/api/data/get"
        params = {
            "type": "RPT_F10_CORETHEME_CONTENT",
            "sty": "SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,KEYWORD,MAINPOINT,MAINPOINT_CONTENT,KEY_CLASSIF,KEY_CLASSIF_CODE,IS_POINT,IS_HISTORY",
            "quoteColumns": "",
            "filter": f'(SECUCODE="{code}.{prefix}")',
            "p": "1",
            "ps": "",
            "sr": "1,1",
            "st": "KEY_CLASSIF_CODE,MAINPOINT",
            "source": "HSF10",
            "client": "PC",
            "v": "017865090995106714"
        }
        yield scrapy.Request(
            url=f"{url}?{urlencode(params)}",
            headers=self.headers,
            callback=self.parse_details,
            errback=self.errback,
            cb_kwargs={'base_data': data}
        )

    def parse_details(self, response, base_data):
        json_data = json.loads(response.text)
        if json_data['result']:
            share_code = base_data['code']  # 股票代码
            subject_details = json_data['result'].get('data')  # 题材详情
            source = base_data['detail_url']    # 来源网址


            main_item = {}
            main_item['share_code'] = share_code
            main_item['subject_details'] = subject_details
            main_item['source'] = source
            main_item['md5_value'] = hash_md5(f"{share_code}")
            main_item['_table'] = 'listing_stock_subject_matter'
            yield main_item


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')