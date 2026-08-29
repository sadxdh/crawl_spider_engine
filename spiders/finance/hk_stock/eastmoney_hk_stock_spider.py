"""东方财富港股列表 → stock_hk
参照旧项目 data_crawl_server HkListingInfoSpider:
  list: push2.eastmoney.com/api/qt/clist/get
"""
import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *

# data_crawl_server spider/finance/hk_stock/eastmoney_hk.py
class EastmoneyHkStockSpider(BaseSpider):
    name = 'finance_eastmoney_hk_stock'
    data_table = 'listing_info_ganggu'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'referer': 'https://quote.eastmoney.com/center/gridlist.html',
        'sec-ch-ua': '"Microsoft Edge";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    }

    def start_requests(self):
        for page in range(1, self.end_page + 1):
            url = 'https://push2.eastmoney.com/api/qt/clist/get'
            params = {
                'np': '1',
                'fltt': '1',
                'invt': '2',
                'cb': '',
                'fs': 'm:128+t:3,m:128+t:4,m:128+t:1,m:128+t:2',
                'fields': 'f12,f13,f14,f19,f1,f2,f4,f3,f152,f17,f18,f15,f16,f5,f6',
                'fid': 'f3',
                'pn': str(page),
                'pz': '20',
                'po': '1',
                'dect': '1',
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'wbp2u': '|0|0|0|web',
            }
            request_url = f'{url}?{urlencode(params)}'

            yield scrapy.Request(
                url=request_url,
                method='GET',
                headers=self.headers,
                callback=self.parse_list,
                dont_filter=True,
            )

    def parse_list(self, response):
        result = response.json()
        res_data = result.get('data', {}).get('diff') if result else []
        stock_code = res_data['f12']
        params_dict = {
            'RPT_HKF10_INFO_SECURITYINFO': 'ALL',
            'RPT_HKF10_INFO_ORGPROFILE': 'ALL'
        }
        origin_data = {}
        for report_name, columns in params_dict.items():
            data = self.get_info(stock_code, report_name, columns)
            origin_data.update(data)

        if origin_data:
            yield from self.sava_data(origin_data)

    @staticmethod
    def generate_params(stock_code, report_name, columns):
        params = {
            'reportName': report_name,
            'columns': columns,
            'quoteColumns': '',
            'filter': f'(SECUCODE="{stock_code}.HK")',
            'pageNumber': 1,
            'pageSize': 200,
            'sortTypes': '',
            'sortColumns': '',
            'source': 'F10',
            'client': 'PC'
        }
        return params

    def get_info(self, stock_code, report_name, columns):
        stock_url = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?'
        params = self.generate_params(stock_code, report_name, columns)
        response = common_request(stock_url, method='GET', headers=self.headers, params=params)
        if response:
            try:
                if 'SECURITYINFO' in report_name:
                    data = self.parse_stock_info(response)
                else:
                    data = self.parse_entity_info(response)
                return data
            except Exception as e:
                error_msg = f'url: {stock_url}, 详情解析错误: {e}'
                self.log_error(error_msg)
                # send_dd_msg(self.spider_name, '解析失败', error_msg)
        return {}

    @staticmethod
    def parse_stock_info(response):
        result = response.json()
        res = result.get('result')
        if res:
            datas = res.get('data', list())

            for data in datas:
                security_code = data.get('SECUCODE')
                security_type = data.get('SECURITY_TYPE')
                listing_date = data.get('LISTING_DATE')
                listing_exchange = data.get('TRADE_MARKET')
                listing_plate = data.get('BOARD')
                isin = data.get('ISIN_CODE')

                temp = {
                    'security_code': security_code,
                    'security_type': security_type,
                    'listing_date': listing_date,
                    'listing_exchange': listing_exchange,
                    'listing_plate': listing_plate,
                    'isin': isin,
                }
                return temp
        return {}

    @staticmethod
    def parse_entity_info(response):
        result = response.json()
        res = result.get('result')
        if res:
            datas = res.get('data', list())
            for data in datas:
                entity_name = data.get('ORG_NAME')
                entity_english_name = data.get('ORG_EN_ABBR')
                industry = data.get('BELONG_INDUSTRY')

                chairman_name = data.get('CHAIRMAN')
                secretary_name = data.get('SECRETARY')
                phone = data.get('ORG_TEL')
                fax = data.get('ORG_FAX')
                email = data.get('ORG_EMAIL')
                website = data.get('ORG_WEB')
                office_address = data.get('ADDRESS')
                register_address = data.get('REG_ADDRESS')
                area = data.get('REG_PLACE')
                introduction = data.get('ORG_PROFILE')
                establish_date = data.get('FOUND_DATE')

                temp = {
                    'entity_name': entity_name,
                    'entity_english_name': entity_english_name,
                    'industry': industry,
                    'chairman_name': chairman_name,
                    'secretary_name': secretary_name,
                    'phone': phone,
                    'fax': fax,
                    'email': email,
                    'website': website,
                    'office_address': office_address,
                    'register_address': register_address,
                    'area': area,
                    'introduction': introduction,
                    'establish_date': establish_date,
                }
                return temp
        return {}

    def sava_data(self, data):
        security_code = data.get('SECURITY_CODE')
        if not security_code:
            return
        items = {}
        items['md5_value'] = hash_md5(data['security_code'] + data['entity_name'] + data['listing_date'])
        items['security_code'] = data['security_code']
        items['security_type'] = data['security_type']
        items['listing_date'] = data['listing_date']
        items['listing_exchange'] = data['listing_exchange']
        items['listing_plate'] = data['listing_plate']
        items['isin'] = data['isin']

        items['entity_name'] = data['entity_name']
        items['entity_english_name'] = data['entity_english_name']
        items['industry'] = data['industry']
        items['chairman_name'] = data['chairman_name']
        items['secretary_name'] = data['secretary_name']
        items['phone'] = data['phone']
        items['fax'] = data['fax']
        items['email'] = data['email']
        items['website'] = data['website']
        items['office_address'] = data['office_address']
        items['register_address'] = data['register_address']
        items['area'] = data['area']
        items['introduction'] = data['introduction']
        items['establish_date'] = data['establish_date']
        # insert_data(table='listing_info_ganggu', data=item)
        yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
