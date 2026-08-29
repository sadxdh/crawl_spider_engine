"""
企业预警通 — 非标资产风险爬虫
数据来源：https://www.qyyjt.cn/bond/nonStandardAssetRisk
API：POST https://www.qyyjt.cn/finchinaAPP/v1/finchina-bond/v1/non-standard/list

增量策略：
  - 每页50条
  - 增量：start_page=1 end_page=2（最新100条）
  - 去重字段：md5_value（product_name + risk_type + reveal_date 的 md5）

本地调试：
  scrapy crawl finance_qyyjt_non_standard_asset_risk -a start_page=1 -a end_page=2
"""
import scrapy
from utils.tools import *
from spiders.finance.qyyjt.qyyjt_base_spider import QyyjtBaseSpider



class QyyjtNonStandardAssetRiskSpider(QyyjtBaseSpider):
    """企业预警通非标资产风险爬虫"""

    name = 'finance_qyyjt_non_standard_asset_risk'
    data_table = 'non_standard_asset_risk'
    dedup_fields = ['md5_value']

    custom_settings = {
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 3,
        'DEFAULT_REQUEST_HEADERS': {},
    }

    headers = {
        'accept': 'application/json',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cache-control': 'no-cache',
        'client': 'pc-web;pro',
        'content-type': 'application/json;charset=UTF-8',
        'origin': 'https://www.qyyjt.cn',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://www.qyyjt.cn/bond/nonStandardAssetRisk',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'system': 'new',
        'system1': 'Windows NT 10.0; Win64; x64;Chrome;134.0.0.0',
        'terminal': 'pc-web;pro',
        'user': 'B1033EE3100047FA2CD86806D56DD75BA17A6F0847DD321EC00DCC5D6650A024',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/134.0.0.0 Safari/537.36',
        'ver': '20250318',
    }

    base_url = 'https://www.qyyjt.cn/finchinaAPP/v1/finchina-bond/v1/non-standard/list'
    product_types = {'2': '信托计划', '3': '集合理财', '4': '其他', '5': '基金专户', '6': '期货资管',
                          '7': '私募基金', '9': '融资租赁合同', '10': '定向融资'}
    risk_types = {1: '风险提示', 2: '已违约', 3: '已偿还'}
    is_paid_back = {'0': '未偿还', '1': '已偿还'}

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            skip = self.page_to_skip(page)
            headers = self._get_auth_headers(self.headers)
            if not headers:
                self.log_warning(f'第 {page} 页无 token，跳过')
                continue
            body = {
                'keyword': '', 'regionCodes': '', 'financerAreaCodes': '',
                'sort': 'BD0270_015:desc', 'type': '', 'type1': '',
                'isUDIC': '', 'func': '/app/appNonStandardDefaultRisk',
                'from': skip, 'riskType': '', 'disclosureStartDate': '',
                'disclosureEndDate': '', 'size': 50,
            }
            yield scrapy.Request(
                url=self.base_url,
                method='POST',
                headers=headers,
                body=json.dumps(body),
                callback=self.parse_list,
                errback=self.errback,
                meta={'page': page},
                dont_filter=True,
            )

    def parse_list(self, response):
        result = response.json()['data']['data']
        for data in result:
            product_name = data['productName']
            product_type = data['productType']
            risk_type = data['riskType']
            amount = data.get('defaultAmount')
            financing_party = data.get('financingParty')
            finally_financing_party = None
            trustee = data.get('managementParty')
            guarantor = data.get('guaranteeParty')
            lead_underwriter = data.get('salesAgency')
            custodian = data.get('custodian')
            principal = data.get('attorneyName')
            buyback_party = data.get('counterpurchaseName')
            lessor = None
            is_repay = data.get('isPaidBack')
            region = data.get('province')
            reveal_date = data.get('disclosureDate')

            product_type = self.product_types.get(product_type, product_type)
            risk_type = self.risk_types.get(risk_type, risk_type)
            is_repay = self.is_paid_back.get(is_repay)

            md5_value = hash_md5(product_name + risk_type + str(reveal_date))

            items = {}
            # item.spider_name = self.spider_name
            items['product_name'] = product_name
            items['product_type'] = product_type
            items['risk_type'] = risk_type
            items['amount'] = amount
            items['financing_party'] = financing_party
            items['finally_financing_party'] = finally_financing_party
            items['trustee'] = trustee
            items['guarantor'] = guarantor
            items['lead_underwriter'] = lead_underwriter
            items['custodian'] = custodian
            items['principal'] = principal
            items['buyback_party'] = buyback_party
            items['lessor'] = lessor
            items['is_repay'] = is_repay
            items['region'] = region
            items['reveal_date'] = reveal_date
            items['md5_value'] = md5_value
            # insert_data('non_standard_asset_risk', item)
            yield items
