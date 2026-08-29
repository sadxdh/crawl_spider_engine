import hashlib, scrapy
import math
from urllib.parse import urlencode
from spiders.finance.gridlist_enterprise.llm_kit import CustomLlmChat
from spiders.base_spider import BaseSpider
from utils.tools import *

class TwoNetworksDelistingSpider(BaseSpider):
    name = 'two_networks_delisting'
    data_table = 'enterprise_listing_status'
    dedup_fields = ['stock_code']
    custom_settings = {
        'CONCURRENT_REQUESTS': 1, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        },
        #'COOKIES_ENABLED': True  # 使用cookie字段必须得要
    }
    proxy_type = 'long_proxy'

    headers = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Referer": "https://quote.eastmoney.com/center/gridlist.html",
        "Sec-Fetch-Dest": "script",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
        "sec-ch-ua": "\"Not;A=Brand\";v=\"8\", \"Chromium\";v=\"150\", \"Google Chrome\";v=\"150\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    qw_ask = CustomLlmChat()


    def start_requests(self):
        url = "https://push2.eastmoney.com/webguest/api/qt/clist/get"
        params = {
            "timil": "1",
            "np": "1",
            "fltt": "1",
            "invt": "2",
            "cb": "",
            "fs": "m:0+s:3",
            "fields": "f12,f13,f14,f1,f2,f4,f3,f152,f5,f6,f18,f17,f15,f16,f33",
            "fid": "f3",
            "pn": "1",
            "pz": "20",
            "po": "1",
            "dect": "1",
            "ut": "",
            "wbp2u": "|0|0|0|web",
            "_": ""
        }
        full_url = f"{url}?{urlencode(params)}"

        yield scrapy.Request(
            url=full_url,
            headers=self.headers,
            callback=self.get_all_page,
            dont_filter=True,
        )

    def get_all_page(self, response):
        json_data = json.loads(response.text)
        total_num = json_data['data']['total']
        for page in range(1, math.ceil(total_num / 20)):
            url = "https://push2.eastmoney.com/webguest/api/qt/clist/get"
            params = {
                "timil": "1",
                "np": "1",
                "fltt": "1",
                "invt": "2",
                "cb": "",
                "fs": "m:0+s:3",
                "fields": "f12,f13,f14,f1,f2,f4,f3,f152,f5,f6,f18,f17,f15,f16,f33",
                "fid": "f3",
                "pn": str(page),
                "pz": "20",
                "po": "1",
                "dect": "1",
                "ut": "",
                "wbp2u": "|0|0|0|web",
                "_": ""
            }
            full_url = f"{url}?{urlencode(params)}"
            yield scrapy.Request(
                url=full_url,
                headers=self.headers,
                callback=self.parse_list,
                dont_filter=True,
            )

    def clean_llm_result(self, res):
        if not res:
            return ""

        res = re.sub(r"<think>.*?</think>", "", res, flags=re.S).strip()
        res = re.sub(r"^```(?:json)?", "", res, flags=re.I).strip()
        res = re.sub(r"```$", "", res).strip()

        match = re.search(r"\{.*\}", res, flags=re.S)
        if match:
            return match.group(0)

        return res

    def parse_list(self, response):
        json_data = json.loads(response.text)
        for data_list in json_data['data']['diff']:
            now_code = data_list['f12']
            company_name = data_list['f14']
            ask_result = self.qw_ask.chat(now_code, company_name)
            ask_data = self.clean_llm_result(ask_result)
            print(ask_data)
            stock_code = json.loads(ask_data)['old_code']
            if stock_code and stock_code != now_code:
                check_res = self.parse_check(stock_code)
                if check_res:
                    check_data = json.loads(check_res.text)
                    try:
                        if check_data['data']['f292'] == 7:
                            data_items = {}
                            data_items['stock_code'] = stock_code
                            data_items['company_name'] = company_name
                            data_items['website'] = 'quote.eastmoney.com'
                            yield data_items
                    except:
                        self.log_info("请求失败，结果数据不对")


    def parse_check(self, stock_code):
        print(stock_code)
        headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            # "Referer": "https://so.eastmoney.com/web/s?keyword=600634",
            "Sec-Fetch-Dest": "script",
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
            "sec-ch-ua": "\"Not;A=Brand\";v=\"8\", \"Chromium\";v=\"150\", \"Google Chrome\";v=\"150\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\""
        }
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "cb": "",
            "ut": "",
            "fields": "f57,f58,f59,f152,f43,f169,f170,f60,f44,f45,f168,f50,f47,f48,f49,f46,f78,f85,f86,f169,f117,f107,f111,f116,f117,f118,f163,f171,f113,f114,f115,f161,f162,f164,f168,f172,f177,f180,f181,f292,f751,f752",
            "secid": f"1.{stock_code}",
            "invt": "2",
            "_": ""
        }
        response = curl_cffi_request(url, headers=headers, params=params, proxies_type=True)
        return response



    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
