import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *


class IpoDeclareEastBseSpider(BaseSpider):
    name = 'ipo_declare_east_bse'
    data_table = 'entity_ipo_declare_a_shares'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://data.eastmoney.com/xg/ipo/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    }
    base_url = 'https://datacenter-web.eastmoney.com/api/data/v1/get'

    @staticmethod
    def generate_params(page):
        params = {
            'callback': '',
            'sortColumns': 'UPDATE_DATE,ORG_CODE',
            'sortTypes': '-1,-1',
            'pageSize': '50',
            'pageNumber': page,
            'reportName': 'RPT_IPO_INFOALLNEW',
            'columns': 'SECURITY_CODE,STATE,REG_ADDRESS,INFO_CODE,CSRC_INDUSTRY,ACCEPT_DATE,DECLARE_ORG,'
                       'PREDICT_LISTING_MARKET,LAW_FIRM,ACCOUNT_FIRM,ORG_CODE,UPDATE_DATE,RECOMMEND_ORG,'
                       'IS_REGISTRATION',
            'source': 'WEB',
            'client': 'WEB',
            'filter': '(PREDICT_LISTING_MARKET="北交所")'
        }
        return params

    @staticmethod
    def generate_detail_params(security_code):
        params = {
            'callback': '',
            'filter': f'(SECURITY_CODE="{security_code}")',
            'columns': 'ISSUER_NAME,ACCEPT_DATE,SECURITY_NAME_ABBR,FINANCE_AMT,CHECK_STATUS,UPDATE_DATE,'
                       'REG_ADDRESS,CSRC_INDUSTRY,RECOMMEND_ORG,SPONSOR,ACCOUNT_FIRM,SIGN_ACCOUNTANT,'
                       'LAW_FIRM,SIGN_LAWYER,EVALUATE_ORG,SIGN_APPRAISER,STATE,END_DATE,TOLIST_MARKET',
            'reportName': 'RPT_REGISTERED_INFO'
        }
        return params

    @staticmethod
    def generate_ipo_params(security_code):
        params = {
            'callback': '',
            'filter': f'(SECURITY_CODE="{security_code}")',
            'columns': 'END_DATE,CHECK_STATUS',
            'source': 'WEB',
            'client': 'WEB',
            'reportName': 'RPT_BJS_REGIPO_CHECKPROCESS',
            'sortColumns': 'END_DATE',
            'sortTypes': '1',
        }
        return params

    def start_requests(self):
        for page in range(self.start_page - 1, self.end_page):
            params = self.generate_params(page)
            req_url = f'{self.base_url}?{urlencode(params)}'
            yield scrapy.Request(
                url=req_url,
                callback=self.get_list,
                dont_filter=True,
                headers=self.headers,
            )

    def get_list(self, response):
        result = response.json()['result']['data']
        for res in result:
            security_code = res['SECURITY_CODE']
            params = self.generate_ipo_params(security_code)
            req_url = f'{self.base_url}?{urlencode(params)}'
            yield scrapy.Request(
                url=req_url,
                callback=self.get_ipo_process,
                dont_filter=True,
                headers=self.headers,
                cb_kwargs={'security_code': security_code}
            )

    def get_ipo_process(self, response, security_code):
        ipo_process = []
        result = response.json()['result']['data']
        for data in result:
            publish_date = match_text(data['END_DATE'])
            examine_status = data['CHECK_STATUS']
            temp = {'publish_date': publish_date, 'examine_status': examine_status}
            ipo_process.append(temp)

        ipo_process = str(ipo_process)
        params = self.generate_detail_params(security_code)
        req_url = f'{self.base_url}?{urlencode(params)}'
        yield scrapy.Request(
            url=req_url,
            callback=self.parse_ipo_base_info,
            dont_filter=True,
            headers=self.headers,
            cb_kwargs={'ipo_process': ipo_process}
        )

    def parse_ipo_base_info(self, response, ipo_process):
        result = response.json()['result']
        if result:
            res = result['data'][0]
            entity_name = res['ISSUER_NAME']
            acceptance_date = res['ACCEPT_DATE']
            update_date = match_text(res['UPDATE_DATE'])
            financing_amount = res['FINANCE_AMT']
            examine_status = res['CHECK_STATUS']
            industry = res['CSRC_INDUSTRY']
            industry_sponsorship = res.get('RECOMMEND_ORG')
            representative_person = res.get('SPONSOR')
            accounting_firm = res.get('ACCOUNT_FIRM')
            accountant = res.get('SIGN_ACCOUNTANT')
            law_firm = res.get('LAW_FIRM')
            lawyer = res.get('SIGN_LAWYER')
            evaluation_agency = res.get('EVALUATE_ORG')
            evaluator = res.get('SIGN_APPRAISER')
            proposed_listing_location = res['TOLIST_MARKET']
            registered_address = res['REG_ADDRESS']

            md5_value = hash_md5(entity_name + update_date + examine_status)
            items = {}
            items['entity_name'] = entity_name
            items['acceptance_date'] = acceptance_date
            items['update_date'] = update_date
            items['financing_amount'] = financing_amount
            items['examine_status'] = examine_status
            items['proposed_listing_location'] = proposed_listing_location
            items['industry'] = industry
            items['industry_sponsorship'] = industry_sponsorship
            items['representative_person'] = representative_person
            items['accounting_firm'] = accounting_firm
            items['accountant'] = accountant
            items['law_firm'] = law_firm
            items['lawyer'] = lawyer
            items['evaluation_agency'] = evaluation_agency
            items['evaluator'] = evaluator
            items['registered_address'] = registered_address
            items['ipo_status'] = ipo_process
            items['source'] = '北交所'
            items['md5_value'] = md5_value
            # insert_data(table='entity_ipo_declare_a_shares', data=item)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
