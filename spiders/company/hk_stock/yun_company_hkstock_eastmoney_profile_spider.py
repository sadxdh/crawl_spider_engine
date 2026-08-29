from scrapy import FormRequest
from spiders.base_spider import BaseSpider
from utils.mysql_tools import select_data
from utils.tools import *
from utils.time_kit import *
import time


class YunCompanyProfileSpider(BaseSpider):
    name = 'yun_company_hkstock_eastmoney_profile'
    default_origin_url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
    headers = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Origin": "https://emweb.securities.eastmoney.com",
        "Referer": "https://emweb.securities.eastmoney.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
    }
    data_table = 'listing_hk_entity_info'
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    def start_requests(self):
        code_list = select_data(
            table='stock_hk_hkex', data=['stock_code'],
            suffix='GROUP BY stock_code ORDER BY stock_code'
        )
        for code in code_list:
            stock_code = code['stock_code']
            for report_name in ['RPT_HKF10_INFO_ORGPROFILE', 'RPT_HKF10_INFO_SECURITYINFO']:
                params = {
                    "reportName": f"{report_name}",
                    "columns": "ALL",
                    "quoteColumns": "",
                    "filter": f'(SECUCODE="{stock_code}.HK")',
                    "pageNumber": "1",
                    "pageSize": "200",
                    "sortTypes": "",
                    "sortColumns": "",
                    "source": "F10",
                    "client": "PC",
                }
                yield FormRequest(
                    url=self.default_origin_url,
                    method='get',
                    headers=self.headers,
                    formdata=params,
                    callback=self.parse,
                    dont_filter=True
                )

    def parse(self, response, **kwargs):

        result = response.json()
        result = result['result']
        if result:
            datas = result['data']
            for data in datas:
                stock_code = data.get('SECUCODE')
                entity_name = data.get('ORG_NAME')
                if entity_name:
                    entity_name_en = data.get('ORG_EN_ABBR')
                    register_place = data.get('REG_PLACE')
                    incorporation_date = data.get('FOUND_DATE')
                    register_address = data.get('REG_ADDRESS')
                    industry = data.get('BELONG_INDUSTRY')
                    chairman = data.get('CHAIRMAN')
                    secretary = data.get('SECRETARY')
                    employee_count = data.get('EMP_NUM')
                    office_address = data.get('ADDRESS')
                    auditor = data.get('ACCOUNT_FIRM')
                    website = data.get('ORG_WEB')
                    email = data.get('ORG_EMAIL')
                    year_end_date = data.get('YEAR_SETTLE_DAY')
                    tel = data.get('ORG_TEL')
                    fax = data.get('ORG_FAX')
                    summary = data.get('ORG_PROFILE')
                    md5_value = hash_md5(stock_code)

                    item = {}
                    item['md5_value'] = md5_value
                    item['stock_code'] = stock_code
                    item['entity_name'] = entity_name
                    item['entity_name_en'] = entity_name_en
                    item['register_place'] = register_place
                    item['register_address'] = register_address
                    item['incorporation_date'] = incorporation_date
                    item['industry'] = industry
                    item['chairman'] = chairman
                    item['secretary'] = secretary
                    item['employee_count'] = employee_count
                    item['office_address'] = office_address
                    item['auditor'] = auditor
                    item['year_end_date'] = year_end_date
                    item['website'] = website
                    item['email'] = email
                    item['tel'] = tel
                    item['fax'] = fax
                    item['summary'] = summary

                    yield item
                else:
                    stock_name = data.get('SECURITY_NAME_ABBR')
                    listing_date = data.get('LISTING_DATE')
                    share_type = data.get('SECURITY_TYPE')
                    issue_price = data.get('ISSUE_PRICE')
                    issue_num = data.get('ISSUE_NUM')
                    lot_size = data.get('TRADE_UNIT')
                    face_value = data.get('PAR_VALUE')
                    exchange = data.get('TRADE_MARKET')
                    board = data.get('BOARD')
                    isin_code = data.get('ISIN_CODE')
                    sh_hk_stock_connect = data.get('GANGGUTONGBIAODIHU')
                    sz_hk_stock_connect = data.get('GANGGUTONGBIAODISHEN')
                    md5_value = hash_md5(stock_code)

                    item = {}
                    item['md5_value'] = md5_value
                    item['stock_code'] = stock_code
                    item['stock_name'] = stock_name
                    item['listing_date'] = listing_date
                    item['share_type'] = share_type
                    item['issue_price'] = issue_price
                    item['issue_num'] = issue_num
                    item['lot_size'] = lot_size
                    item['face_value'] = face_value
                    item['exchange'] = exchange
                    item['board'] = board
                    item['isin_code'] = isin_code
                    item['sh_hk_stock_connect'] = sh_hk_stock_connect
                    item['sz_hk_stock_connect'] = sz_hk_stock_connect

                    yield item
