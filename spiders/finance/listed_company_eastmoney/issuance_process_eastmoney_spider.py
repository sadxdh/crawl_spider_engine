import hashlib, scrapy
import math
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.mysql_tools import select_data
from utils.tools import *


# https://quote.eastmoney.com/center/gridlist.html#hs_a_board
# 发展历程
class IssuanceProcessEastmoneySpider(BaseSpider):
    name = 'issuance_process_eastmoney'
    data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 5, 'DOWNLOAD_DELAY': 1,
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
        details_url = f"https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code={prefix}{code}&color=b#/gsgk"
        yield from self.get_details({'detail_url': details_url, 'code': code, 'prefix': prefix})

    def get_details(self, data):
        details_url = data['detail_url']
        code = data['code']
        prefix = data['prefix']
        url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        params = {
            "reportName": "RPT_PCF10_ORG_ISSUEINFO",
            "columns": "ALL",
            "quoteColumns": "",
            "filter": f'(SECUCODE="{code}.{prefix}")',
            "pageNumber": "1",
            "pageSize": "1",
            "sortTypes": "",
            "sortColumns": "",
            "source": "HSF10",
            "client": "PC",
            "v": ""
        }
        yield scrapy.Request(
            url=f"{url}?{urlencode(params)}",
            headers=self.headers,
            callback=self.parse_details,
            cb_kwargs={'details_url': details_url, 'code': code, 'prefix': prefix}
        )

    def parse_details(self, response, details_url, code, prefix):
        json_data = response.json()['result']['data']
        if json_data and len(json_data) != 0:
            data = json_data[0]
            share_code = code  # 股票代码
            recommendation_institution = data['STR_BAOJIAN']  # 保荐机构
            lead_underwriter = data['STR_ZHUCHENGXIAO']  # 主承销商
            register_time = data['FOUND_DATE']  # 成立日期
            listing_time = data['LISTING_DATE']  # 上市日期
            profit_margin = data['AFTER_ISSUE_PE']  # 发行市盈率(倍)
            online_release_date = data['ONLINE_ISSUE_DATE']  # 网上发行日期
            issuance_method = data['ISSUE_WAY']  # 发行方式
            par_value = data['PAR_VALUE']  # 每股面值(元)
            total_issue_num = data['TOTAL_ISSUE_NUM']  # 发行量(股)
            issue_price = data['ISSUE_PRICE']  # 每股发行价(元)
            dec_sumissuefee = data['DEC_SUMISSUEFEE']  # 发行费用(元)
            total_funds = data['TOTAL_FUNDS']  # 发行总市值(元)
            net_raise_funds = data['NET_RAISE_FUNDS']  # 募集资金净额(元)
            open_price = data['OPEN_PRICE']  # 首日开盘价(元)
            close_price = data['CLOSE_PRICE']  # 首日收盘价(元)
            turnoverrate = data['TURNOVERRATE']  # 首日换手率
            high_price = data['HIGH_PRICE']  # 首日最高价(元)
            offline_vap_ratio = data['OFFLINE_VAP_RATIO']  # 网下配售中签率
            online_issue_lwr = data['ONLINE_ISSUE_LWR']  # 定价中签率
            basic_data = json.dumps(data, ensure_ascii=False)

            main_item = {}
            main_item['share_code'] = share_code
            main_item['recommendation_institution'] = recommendation_institution
            main_item['lead_underwriter'] = lead_underwriter
            main_item['register_time'] = register_time
            main_item['listing_time'] = listing_time
            main_item['profit_margin'] = profit_margin
            main_item['online_release_date'] = online_release_date
            main_item['issuance_method'] = issuance_method
            main_item['par_value'] = par_value
            main_item['total_issue_num'] = total_issue_num
            main_item['issue_price'] = issue_price
            main_item['dec_sumissuefee'] = dec_sumissuefee
            main_item['total_funds'] = total_funds
            main_item['net_raise_funds'] = net_raise_funds
            main_item['open_price'] = open_price
            main_item['close_price'] = close_price
            main_item['turnoverrate'] = turnoverrate
            main_item['high_price'] = high_price
            main_item['offline_vap_ratio'] = offline_vap_ratio
            main_item['online_issue_lwr'] = online_issue_lwr
            main_item['source'] = details_url
            main_item['md5_value'] = hash_md5(f"{details_url}{share_code}")
            # insert_data('listing_stock_issue', main_item)
            main_item['_table'] = 'listing_stock_issue'
            main_item['basic_data'] = basic_data
            yield main_item



    def errback(self, failure):
            self.log_error(f'请求失败: {failure.request.url} — {failure.value}')