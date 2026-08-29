import hashlib, scrapy
import math
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.finance.listed_company_eastmoney.fs_key_value import fs_value
from utils.mysql_tools import select_data
from utils.tools import *
from utils.time_kit import *


# https://quote.eastmoney.com/center/gridlist.html#hs_a_board
# 十大股东
class ShareholderInformationEastmoneySpider(BaseSpider):
    name = 'shareholder_information_eastmoney'
    data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 10, 'DOWNLOAD_DELAY': 0.3,
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

    def __init__(self, stock_codes=None, limit_count=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 处理传入的股票代码参数
        if stock_codes:
            self.stock_codes = [code.strip() for code in stock_codes.split(',')]
        else:
            self.stock_codes = None
        self.limit_count = int(limit_count) if limit_count else None

    def start_requests(self):
        # 根据是否传入 stock_codes 构建不同的 suffix
        if self.stock_codes:
            codes_str = ','.join([f"'{code}'" for code in self.stock_codes])
            condition = f'stock_code IN ({codes_str}) '
        else:
            condition = None

        code_list = select_data(
            table='stock_hsj', data=['stock_code', 'status', 'area'],
            condition=condition,
            suffix='GROUP BY stock_code ORDER BY stock_code'
        )
        for code in code_list:
            stock_code = code['stock_code']
            status = code['status']
            f13 = code['area']
            if status == 1:
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
        if f13 == 1:
            prefix = "SH"
        details_url = f"https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code={prefix}{code}&color=b#/gdyj"
        yield from self.get_date({'detail_url': details_url, 'code': code, 'prefix': prefix})

    def get_date(self, data):
        # 十大流通股东
        code = data['code']
        prefix = data['prefix']
        detail_url = data['detail_url']
        url_free = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        params_free = {
            "reportName": "RPT_F10_EH_FREEHOLDERSDATE",
            "columns": "SECUCODE,END_DATE",
            "quoteColumns": "",
            "filter": f'(SECUCODE="{code}.{prefix}")',
            "pageNumber": "1",
            "pageSize": "",
            "sortTypes": "-1",
            "sortColumns": "END_DATE",
            "source": "HSF10",
            "client": "PC",
            "v": ""
        }
        yield scrapy.Request(
            url=f"{url_free}?{urlencode(params_free)}",
            headers=self.headers,
            callback=self.parse_date_free,
            cb_kwargs={'detail_url': detail_url, 'code': code, 'prefix': prefix}
        )


        # 十大股东
        url= "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        params = {
            "reportName": "RPT_F10_EH_HOLDERSDATE",
            "columns": "SECUCODE,END_DATE",
            "quoteColumns": "",
            "filter": f'(SECUCODE="{code}.{prefix}")',
            "pageNumber": "1",
            "pageSize": "",
            "sortTypes": "-1",
            "sortColumns": "END_DATE",
            "source": "HSF10",
            "client": "PC",
            "v": "06539322007297044"
        }
        yield scrapy.Request(
            url=f"{url}?{urlencode(params)}",
            headers=self.headers,
            callback=self.parse_date,
            cb_kwargs={'detail_url': detail_url, 'code': code, 'prefix': prefix}
        )

    def parse_date_free(self, response, detail_url, code, prefix):
        json_data = response.json()
        if json_data['result']:
            for data in json_data['result'].get('data', [])[:self.limit_count]:
                if data.get('END_DATE'):
                    date_data = data['END_DATE']
                    yield from self.get_details_free({'detail_url': detail_url, 'code': code, 'prefix': prefix, 'date': date_data})

    def parse_date(self, response, detail_url, code, prefix):
        json_data = response.json()
        if json_data['result']:
            for data in json_data['result'].get('data', [])[:self.limit_count]:
                if data.get('END_DATE'):
                    date_data = data['END_DATE']
                    yield from self.get_details({'detail_url': detail_url, 'code': code, 'prefix': prefix, 'date': date_data})

    def get_details_free(self, data):
        code = data['code']
        prefix = data['prefix']
        date = data['date']

        url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        params = {
            "reportName": "RPT_F10_EH_FREEHOLDERS",
            "columns": "ALL",
            "quoteColumns": "",
            "filter": f"""(SECUCODE="{code}.{prefix}")(END_DATE='{date.split(" ")[0]}')""",
            "pageNumber": "1",
            "pageSize": "",
            "sortTypes": "1",
            "sortColumns": "HOLDER_RANK",
            "source": "HSF10",
            "client": "PC",
            "v": ""
        }
        yield scrapy.Request(
            url=f"{url}?{urlencode(params)}",
            headers=self.headers,
            callback=self.parse_details_free,
            cb_kwargs={'base_data': data}
        )

    def parse_details_free(self, response, base_data):
        json_data = response.json()
        if json_data['result']:
            for data in json_data['result'].get('data', []):
                share_code = base_data['code']  # 股票代码
                shareholding_date = base_data['date'] # 持股日期
                shareholder_name = data['HOLDER_NAME']  # 股东名称
                shareholder_nature = data['HOLDER_TYPE']  # 股东性质
                shares_type = data['SHARES_TYPE'] # 股份类型
                hold_num = data['HOLD_NUM'] # 持股数(股)
                hold_num_ratio = data['FREE_HOLDNUM_RATIO'] # 持股比例(%)
                hold_num_change = data['HOLD_NUM_CHANGE'] # 增减(股)
                change_ratio = data['CHANGE_RATIO'] # 变动比例(%)
                shareholder_type = "十大流通股东" # 股东类型
                source = base_data['detail_url'] # 来源网址
                basic_data = json.dumps(data, ensure_ascii=False)

                main_item = {}
                main_item['share_code'] = share_code
                main_item['shareholding_date'] = shareholding_date
                main_item['shareholder_name'] = shareholder_name
                main_item['shareholder_nature'] = shareholder_nature
                main_item['shares_type'] = shares_type
                main_item['hold_num'] = hold_num
                main_item['hold_num_ratio'] = hold_num_ratio
                main_item['hold_num_change'] = hold_num_change
                main_item['change_ratio'] = change_ratio
                main_item['shareholder_type'] = shareholder_type
                main_item['source'] = source
                main_item['md5_value'] = hash_md5(f"{source}{share_code}{shareholding_date}{shareholder_name}{shareholder_type}")
                # insert_data('listing_stock_top_shareholder', main_item)
                main_item['_table'] = 'listing_stock_top_shareholder'
                main_item['basic_data'] = basic_data
                yield main_item


    def get_details(self, data):
        code = data['code']
        prefix = data['prefix']
        date = data['date']

        url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        params = {
            "reportName": "RPT_F10_EH_HOLDERS",
            "columns": "ALL",
            "quoteColumns": "",
            "filter": f"""(SECUCODE="{code}.{prefix}")(END_DATE='{date.split(" ")[0]}')""",
            "pageNumber": "1",
            "pageSize": "",
            "sortTypes": "1",
            "sortColumns": "HOLDER_RANK",
            "source": "HSF10",
            "client": "PC",
            "v": ""
        }
        yield scrapy.Request(
            url=f"{url}?{urlencode(params)}",
            headers=self.headers,
            callback=self.parse_details,
            cb_kwargs={'base_data': data}
        )

    def parse_details(self, response, base_data):
        json_data = response.json()
        if json_data['result']:
            for data in json_data['result'].get('data', []):
                share_code = base_data['code']  # 股票代码
                shareholding_date = base_data['date']  # 持股日期
                shareholder_name = data['HOLDER_NAME']  # 股东名称
                shareholder_nature = None  # 股东性质
                shares_type = data['SHARES_TYPE']  # 股份类型
                hold_num = data['HOLD_NUM']  # 持股数(股)
                hold_num_ratio = data['HOLD_NUM_RATIO']  # 持股比例(%)
                hold_num_change = data['HOLD_NUM_CHANGE']  # 增减(股)
                change_ratio = data['CHANGE_RATIO']  # 变动比例(%)
                shareholder_type = "十大股东"  # 股东类型
                source = base_data['detail_url']  # 来源网址
                basic_data = json.dumps(data, ensure_ascii=False)


                main_item = {}
                main_item['share_code'] = share_code
                main_item['shareholding_date'] = shareholding_date
                main_item['shareholder_name'] = shareholder_name
                main_item['shareholder_nature'] = shareholder_nature
                main_item['shares_type'] = shares_type
                main_item['hold_num'] = hold_num
                main_item['hold_num_ratio'] = hold_num_ratio
                main_item['hold_num_change'] = hold_num_change
                main_item['change_ratio'] = change_ratio
                main_item['shareholder_type'] = shareholder_type
                main_item['source'] = source
                main_item['md5_value'] = hash_md5(f"{source}{share_code}{shareholding_date}{shareholder_name}{shareholder_type}")
                # insert_data('listing_stock_top_shareholder', main_item)
                main_item['_table'] = 'listing_stock_top_shareholder'
                main_item['basic_data'] = basic_data
                yield main_item

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')