"""
企业预警通 — 银行授信额度爬虫
数据来源：https://www.qyyjt.cn/finance/creditLimit
API：POST https://www.qyyjt.cn/finchinaAPP/getFinCreditDetailList.action

增量策略：
  - 每页50条
  - 增量：start_page=1 end_page=2（最新100条）
  - 去重字段：md5_value（entity_name + credit_institutions + reveal_date 的 md5）

本地调试：
  scrapy crawl finance_qyyjt_bank_credit -a start_page=1 -a end_page=2
"""
import scrapy
from spiders.finance.qyyjt.qyyjt_base_spider import QyyjtBaseSpider
from utils.mysql_tools import select_data
from utils.tools import *


class QyyjtBankCreditSpider(QyyjtBaseSpider):
    """企业预警通银行授信额度爬虫"""

    name = 'finance_qyyjt_bank_credit'
    data_table = 'bank_credit'
    dedup_fields = ['md5_value']

    custom_settings = {
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 3,
        'DEFAULT_REQUEST_HEADERS': {},
    }

    headers = {
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive',
        'Origin': 'https://www.qyyjt.cn',
        'Referer': 'https://www.qyyjt.cn/finance/creditLimit',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/127.0.0.0 Safari/537.36',
        'accept': 'application/json',
        'client': 'pc-web;pro',
        'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'system': 'new',
        'terminal': 'pc-web;pro',
        'ver': '20240718',
    }

    base_url = 'https://www.qyyjt.cn/finchinaAPP/getFinCreditDetailList.action'

    enterprise_nature = {
        1: "央企",
        2: "地方国企",
        3: "其他国企",
        4: "民营企业",
        5: "集体企业",
        6: "外资企业",
        7: "中外合资企业"
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            skip = self.page_to_skip(page)
            headers = self._get_auth_headers(self.headers)
            if not headers:
                self.log_warning(f'第 {page} 页无 token，跳过')
                continue
            body = (
                f'entityName=&areaCode=&containStatus=&urbanBondType='
                f'&skip={skip}&pagesize=50&noDataId=true&endDate='
            )
            time.sleep(random.randint(5, 20))
            yield scrapy.Request(
                url=self.base_url,
                method='POST',
                headers=headers,
                body=body,
                callback=self.parse_list,
                errback=self.errback,
                dont_filter=True,
            )

    def parse_list(self, response):
        result = response.json()['data']
        for data in result:
            credit_institutions = data.get('creditOrgName', '')
            entity_name = data['entityName']
            one_industry = data.get('swIndustryTopLevel')
            entity_rating = data.get('entityRatingSource')
            enterprise_nature_id = data.get('enterpriseNature')
            entity_type = self.enterprise_nature.get(enterprise_nature_id) if enterprise_nature_id else None

            credit_limit = data.get('creditLine')
            used = data.get('creditLineUsed')
            not_used = data.get('creditLineUnused')
            due_date = data['endDate']
            reveal_date = data['discloureDate']
            county_code = data.get('countyCode')
            region = self.get_region_info(county_code) if county_code else None
            md5_value = hash_md5(entity_name + str(credit_institutions) + str(reveal_date))

            items = {}
            items['credit_institutions'] = credit_institutions
            items['entity_name'] = entity_name
            items['sw_level_one_industry'] = one_industry
            items['latest_entity_rating'] = entity_rating
            items['entity_type'] = entity_type
            items['region'] = region
            items['credit_limit'] = credit_limit
            items['used'] = used
            items['not_used'] = not_used
            items['due_date'] = due_date
            items['reveal_date'] = reveal_date
            items['md5_value'] = md5_value
            # insert_data('bank_credit', item)
            yield items

    @staticmethod
    def get_region_info(district_code):
        filed = ['district']
        data = select_data('national_region_info', filed, condition=f'district_code={district_code}')
        result = data[0]['district'] if data else None
        return result
