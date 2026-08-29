import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.mysql_tools import select_data
from utils.tools import *
from utils.time_kit import *

class CompanyHkstockEastmoneyShareholdingStructureSpider(BaseSpider):
    name = 'company_hkstock_eastmoney_shareholding_structure'
    data_table = 'listing_hk_capital_structure'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        },
        # 'RETRY_ENABLED': True,
        # "RETRY_HTTP_CODES": [566],
        # "RETRY_TIMES": 3,  # 失败重试
        #'COOKIES_ENABLED': True  # 使用cookie字段必须得要
    }
    proxy_type = 'long_proxy'

    headers = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Origin": "https://emweb.securities.eastmoney.com",
        "Referer": "https://emweb.securities.eastmoney.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
    }

    sharehold_info = {
        "已发行普通股": 'yfxptg',
        "香港普通股": 'xgptg',
        "内地上市股": 'ndssg',
        "海外上市股": 'hwssg',
        "非上市流通股": 'fssltg',
        "已发行优先股": 'yfxyxg',
    }

    def start_requests(self):
        code_list = select_data(
            table='stock_hk_hkex', data=['stock_code'],
            suffix='GROUP BY stock_code ORDER BY stock_code'
        )
        for code in code_list:
            entity_id = code.get('stock_code')
            if entity_id:
                url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
                params = {
                    "reportName": "RPT_HKF10_INFO_EQUITYSTR",
                    "columns": "SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,CHANGE_DATE,SHARES_TYPE_CODE,SHARES_TYPE,SHARES_NUM,SHARES_RATIO,CHANGE_REASON",
                    "quoteColumns": "",
                    "filter": f'(SECUCODE="{entity_id}.HK")',
                    "pageNumber": 1,
                    "pageSize": "",
                    "sortTypes": 1,
                    "sortColumns": "SHARES_TYPE_CODE",
                    "source": "F10",
                    "client": "PC",
                    "v": "",
                }
                yield scrapy.Request(
                    url=f"{url}?{urlencode(params)}",
                    headers=self.headers,
                    callback=self.parse_details,
                    cb_kwargs={'stock_code': entity_id},
                )

    def parse_details(self, response, stock_code):
        json_data = response.json()
        if json_data['result']:
            item_value = {}
            for key_value in json_data['result'].get('data', []):
                key_name = self.sharehold_info.get(key_value.get('SHARES_TYPE'))
                if key_name:
                    item_value[key_name] = key_value.get('SHARES_NUM')

            stock_code = f'{stock_code}.HK' # 股票代码
            issued_ordinary_shares = item_value.get('yfxptg')  # 已发行普通股(股)
            hk_common_stock = item_value.get('xgptg')    # 香港普通股(股)
            mainland_listed_stocks = item_value.get('ndssg')    # 内地上市股(股)
            overseas_listed_stocks = item_value.get('hwssg')    # 海外上市股(股)
            non_publicly_traded_shares = item_value.get('fssltg')  # 非上市流通股(股)
            issued_preferred_shares = item_value.get('yfxyxg')  # 已发行优先股(股)
            change_reasons = json_data['result']['data'][0].get('CHANGE_REASON')   # 股本变动原因

            main_item = {}
            main_item['stock_code'] = stock_code
            main_item['issued_ordinary_shares'] = issued_ordinary_shares
            main_item['hk_common_stock'] = hk_common_stock
            main_item['mainland_listed_stocks'] = mainland_listed_stocks
            main_item['overseas_listed_stocks'] = overseas_listed_stocks
            main_item['non_publicly_traded_shares'] = non_publicly_traded_shares
            main_item['issued_preferred_shares'] = issued_preferred_shares
            main_item['change_reasons'] = change_reasons
            main_item['md5_value'] = hash_md5(stock_code)
            yield main_item




    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')