import hashlib, scrapy
import math
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.finance.listed_company_eastmoney.fs_key_value import fs_value
from utils.mysql_tools import select_data
from utils.tools import *
from utils.time_kit import *


# https://quote.eastmoney.com/center/gridlist.html#hs_a_board
# 公司概况
class BasicInformationEastmoneySpider(BaseSpider):
    name = 'basic_information_eastmoney'
    data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 8, 'DOWNLOAD_DELAY': 0.3,
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
        if f13 == 1 or f13 == '1':
            prefix = "SH"
        details_url = f"https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code={prefix}{code}&color=b#/gsgk"
        yield from self.get_details({'detail_url': details_url, 'code': code, 'prefix': prefix})

    def get_details(self, data):
        logger.warning(f"spider_name:{self.name}  data:{data}")
        details_url = data['detail_url']
        code = data['code']
        prefix = data['prefix']
        url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        params = {
            "reportName": "RPT_F10_ORG_BASICINFO",
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
            callback=self.get_businessreview_orange,
            cb_kwargs={'details_url': details_url, 'code': code, 'prefix': prefix}
        )

    def get_businessreview_orange(self, response, details_url, code, prefix):
        main_business = []
        # 橙色字体
        url = "https://eminterservice.securities.eastmoney.com/dc-ai-api/api/businessReview/search"
        params = {
            "seCuCode": f"{code}.{prefix}",
            "client": "web",
            "clientType": "pc",
            "clientVersion": "11.8.0",
            "v": ""
        }
        yield scrapy.Request(
            url=f"{url}?{urlencode(params)}",
            headers=self.headers,
            callback=self.get_businessreview_blue,
            cb_kwargs={'details_response': response, 'details_url': details_url, 'code': code, 'prefix': prefix}
        )
    def get_businessreview_blue(self, response, details_response, details_url, code, prefix):
        main_business = []
        for labels in response.json()['data']['labels']:
            if labels['label']:
                main_business.append(labels['label'])
        # 蓝色字体
        url1 = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        params1 = {
            "reportName": "RPT_F10_BASICINFO_ORGLABEL",
            "columns": "SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,ORG_LABEL,ORG_LABEL_CODE",
            "quoteColumns": "",
            "filter": f'(SECUCODE="{code}.{prefix}")',
            "pageNumber": "1",
            "pageSize": "",
            "sortTypes": "",
            "sortColumns": "",
            "source": "HSF10",
            "client": "PC",
            "v": ""
        }
        yield scrapy.Request(
            url=f"{url1}?{urlencode(params1)}",
            headers=self.headers,
            callback=self.parse_details,
            cb_kwargs={'details_response': details_response, 'details_url': details_url, 'code': code, 'prefix': prefix, 'main_business': main_business}
        )

    def parse_details(self, response, details_response, details_url, code, prefix, main_business):
        for data in response.json()['result']['data']:
            if data['ORG_LABEL']:
                main_business.append(data['ORG_LABEL'])
        json_data = details_response.json()['result']['data']
        if json_data and len(json_data) != 0:
            data = json_data[0]
            entity_name = data['ORG_NAME']
            businessreview_data = main_business
            if businessreview_data:
                corporate_tags = '、'.join(businessreview_data)
            else:
                corporate_tags = None
            entity_english_name = data['ORG_NAME_EN']
            share_code = data['SECURITY_CODE']
            stock_name_abbr = data['SECURITY_NAME_ABBR']
            stock_expand_name_abbr = data['EXPAND_NAME_ABBR']
            nature_business = data['ORG_FORM']
            security_type = data['SECURITY_TYPE']
            dongchai_industry = f"{data.get('BOARD_NAME_1LEVEL', '')}-{data.get('BOARD_NAME_2LEVEL', '')}-{data.get('BOARD_NAME_3LEVEL', '')}"
            listed_exchange = data['TRADE_MARKET_ZF']
            csrc_cagetory = data['CSRC_INDUSTRY_NAME']
            general_manager = data['PRESIDENT']
            legal_name = data['LEGAL_PERSON']
            secretaries_name = data['SECRETARY']
            chair_man_name = data['CHAIRMAN']
            securities_affairs_representative = data['SECPRESENT']
            independent_director_name = data['INDEDIRECTORS']
            controlling_shareholder = data['CONTROL_HOLDER']
            proportion_controlling_shareholder = data['CONTROL_DIRECT_RATIO']
            actual_controller = data['REAL_CONTROLER']
            proportion_actual_controller = data['REAL_DIRECT_RATIO']
            revenue_composition = data['INCOME_STRU_NAME']
            introduction = data['ORG_PROFIE']
            number_employees = data['TOTAL_NUM']
            number_management_personnel = data['TATOLNUMBER']
            phone = data['ORG_TEL']
            email = data['ORG_EMAIL']
            fax = data['ORG_FAX']
            website = data['ORG_WEB']
            office_address = data['ADDRESS']
            register_address = data['REG_ADDRESS']
            area = data['REGIONBK']
            postal_code = data['ADDRESS_POSTCODE']
            registered_capital = f"{data['REG_CAPITAL']}"
            business_registration = data['REG_NUM']
            law_firm = data['LEGAL_ADVISER']
            accounting_firm = data['ACCOUNT_FIRM']
            business_scope = data['BUSINESS_SCOPE']

            basic_data = json.dumps(data, ensure_ascii=False)

            if share_code:
                main_item = {}
                main_item['entity_name'] = entity_name
                main_item['corporate_tags'] = corporate_tags
                main_item['entity_english_name'] = entity_english_name
                main_item['share_code'] = share_code
                main_item['stock_name_abbr'] = stock_name_abbr
                main_item['stock_expand_name_abbr'] = stock_expand_name_abbr
                main_item['nature_business'] = nature_business
                main_item['security_type'] = security_type
                main_item['dongchai_industry'] = dongchai_industry
                main_item['listed_exchange'] = listed_exchange
                main_item['csrc_cagetory'] = csrc_cagetory
                main_item['general_manager'] = general_manager
                main_item['legal_name'] = legal_name
                main_item['secretaries_name'] = secretaries_name
                main_item['chair_man_name'] = chair_man_name
                main_item['securities_affairs_representative'] = securities_affairs_representative
                main_item['independent_director_name'] = independent_director_name
                main_item['controlling_shareholder'] = controlling_shareholder
                main_item['proportion_controlling_shareholder'] = proportion_controlling_shareholder
                main_item['actual_controller'] = actual_controller
                main_item['proportion_actual_controller'] = proportion_actual_controller
                main_item['revenue_composition'] = revenue_composition
                main_item['introduction'] = introduction
                main_item['number_employees'] = number_employees
                main_item['number_management_personnel'] = number_management_personnel
                main_item['phone'] = phone
                main_item['email'] = email
                main_item['fax'] = fax
                main_item['website'] = website
                main_item['office_address'] = office_address
                main_item['register_address'] = register_address
                main_item['area'] = area
                main_item['postal_code'] = postal_code
                main_item['registered_capital'] = registered_capital
                main_item['business_registration'] = business_registration
                main_item['law_firm'] = law_firm
                main_item['accounting_firm'] = accounting_firm
                main_item['business_scope'] = business_scope
                main_item['source'] = details_url
                main_item['md5_value'] = hash_md5(f"{details_url}{share_code}")
                # insert_data('listing_entity_info', main_item)
                main_item['basic_data'] = basic_data
                main_item['_table'] = 'listing_entity_info'
                yield main_item


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')