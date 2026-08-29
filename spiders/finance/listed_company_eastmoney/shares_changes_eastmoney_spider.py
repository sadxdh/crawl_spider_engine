import hashlib, scrapy
import math
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.mysql_tools import select_data
from utils.tools import *


# https://quote.eastmoney.com/center/gridlist.html#hs_a_board
# 股本结构 股份变动
class SharesChangesEastmoneySpider(BaseSpider):
    name = 'shares_changes_eastmoney'
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
            if status == 1 or status == "1":
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
        details_url = f"https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code={prefix}{code}&color=b#/gbjg"
        yield from self.get_details({'detail_url': details_url, 'code': code, 'prefix': prefix})

    def get_details(self, data):
        code = data['code']
        prefix = data['prefix']
        url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        params = {
            "reportName": "RPT_F10_EH_EQUITY",
            "columns": "ALL",
            "quoteColumns": "",
            "filter": f'(SECUCODE="{code}.{prefix}")',
            "pageNumber": "1",
            "pageSize": "20",
            "sortTypes": "-1",
            "sortColumns": "END_DATE",
            "source": "HSF10",
            "client": "PC",
            "v": ""
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
            for data in json_data['result'].get('data', []):
                share_code = base_data['code']  # 股票代码
                change_date = data['END_DATE']  # 变动日期
                total_shares = data['TOTAL_SHARES']  # 总股本(股)
                limited_shares = data['LIMITED_SHARES'] # 流通受限股份(股)
                limited_state_legal = data['LIMITED_STATE_LEGAL']   # 国有法人持股(受限)(股)
                unlimited_shares = data['UNLIMITED_SHARES'] # 已流通股份(股)
                listed_a_shares = data['LISTED_A_SHARES']    # 已上市流通A股(股)
                change_reason = data['CHANGE_REASON'] # 变动原因
                source = base_data['detail_url']    # 来源网址
                basic_data = json.dumps(data, ensure_ascii=False)

                main_item = {}
                main_item['share_code'] = share_code
                main_item['change_date'] = change_date
                main_item['total_shares'] = total_shares
                main_item['limited_shares'] = limited_shares
                main_item['limited_state_legal'] = limited_state_legal
                main_item['unlimited_shares'] = unlimited_shares
                main_item['listed_a_shares'] = listed_a_shares
                main_item['change_reason'] = change_reason
                main_item['source'] = source
                main_item['md5_value'] = hash_md5(f"{share_code}:{change_date}")
                main_item['_table'] = 'listing_stock_capital_changes'
                main_item['basic_data'] = basic_data
                yield main_item



    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')