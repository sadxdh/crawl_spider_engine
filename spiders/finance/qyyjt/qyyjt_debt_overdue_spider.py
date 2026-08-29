"""
企业预警通 — 债务逾期爬虫
数据来源：https://www.qyyjt.cn/bond/overdue/debt
API：GET https://www.qyyjt.cn/finchinaAPP/v1/finchina-bond/v1/bond/overdue/debt

增量策略：
  - 每页50条，默认查近1年数据
  - 增量：start_page=1 end_page=2（最新100条）
  - 去重字段：md5_value（entity_name+creditor_name+overdue_amount+overdue_start_date+publish_date 的 md5）

本地调试：
  scrapy crawl finance_qyyjt_debt_overdue -a start_page=1 -a end_page=2
"""
from urllib.parse import urlencode
from utils.time_kit import *
import scrapy
from utils.tools import *
from spiders.finance.qyyjt.qyyjt_base_spider import QyyjtBaseSpider


class QyyjtDebtOverdueSpider(QyyjtBaseSpider):
    """企业预警通债务逾期爬虫"""

    name = 'finance_qyyjt_debt_overdue'
    data_table = 'debt_overdue'
    dedup_fields = ['md5_value']

    custom_settings = {
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 3,
        'DEFAULT_REQUEST_HEADERS': {},
    }

    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cache-control': 'no-cache',
        'client': 'pc-web;pro',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://www.qyyjt.cn/bond/overdue/debt',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'system': 'new',
        'system1': 'Windows NT 10.0; Win64; x64;Chrome;133.0.0.0',
        'terminal': 'pc-web;pro',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/133.0.0.0 Safari/537.36',
        'ver': '20250218'
    }

    base_url = 'https://www.qyyjt.cn/finchinaAPP/v1/finchina-bond/v1/bond/overdue/debt'

    @staticmethod
    def generate_params(skip):
        params = {
            'cityCode': '',
            'countyCode': '',
            'provCode': '',
            'industryFirstCode': '',
            'keyword': '',
            'publishDateFrom': date_through(days=-365),
            'publishDateTo': return_today(date_type='%Y-%m-%d'),
            'size': '50',
            'from': str(skip),
            'keywordEnum': '',
            'isHKListed': '',
            'isHSJListed': '',
            'isIssued': '',
            'isNewThirdBoardListed': '',
            'isUrban': '',
            'isUrbanChild': '',
            'enterpriseNature': '',
            'sortKeyEnum': '',
            'sortOrder': '',
            'endDate': '',
            'isNotListed': '',
            'debtorBusinessType': '',
            'industrySecCode': '',
            'subId': '',
            'isRepaid': '',
        }
        return params

    def start_requests(self):
        today = datetime.now().strftime('%Y-%m-%d')
        year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

        for page in range(self.start_page, self.end_page + 1):
            skip = self.page_to_skip(page)
            headers = self._get_auth_headers(self.headers)
            if not headers:
                self.log_warning(f'第 {page} 页无 token，跳过')
                continue

            params = self.generate_params(skip)
            url = f"{self.base_url}?{urlencode(params)}"

            yield scrapy.Request(
                url=url,
                method="POST",
                headers=headers,
                callback=self.parse_list,
            )

    @staticmethod
    def format_value(value_str):
        if not value_str:
            return ''
        value_float = float(value_str)  # 首先转换为浮点数
        if value_float % 1 == 0:  # 如果小数部分为0
            return int(value_float)  # 转换为整数，去掉'.00'
        else:
            return value_float  # 否则保持浮点数形式

    def parse_list(self, response):
        result = response.json()['data']['list']
        for data in result:
            entity_name = data.get('obligorName')  # 债务人
            debt_type = data.get('debtType')
            coin_type = data.get('currency')
            overdue_amount = data.get('overdueAmount', '')
            overdue_principal = data.get('overduePrincipalAmount')
            overdue_interest = data.get('overdueInterest')
            disclosing_party = data.get('discloserName')
            creditor_name = data.get('creditorName', '')  # 债权人
            overdue_start_date = data.get('overdueStartDate', '')
            repay_schedule = data.get('isRepaid')
            repay_amount = data.get('repayAmount')
            entity_type = data.get('enterpriseNature')
            national_standard_category = data.get('industryFirst')
            national_standard_big_class = data.get('industrySecond')
            national_standard_middle_class = data.get('industryThird')
            national_standard_little_class = data.get('industryFourth')
            region = data.get('area')
            due_date = data.get('endDate')
            publish_date = data.get('publishDate', '')

            overdue_amount = str(overdue_amount).replace(',', '') if overdue_amount else None
            overdue_amount = self.format_value(overdue_amount)
            md5_value = hash_md5(
                entity_name + creditor_name + str(overdue_amount) + str(overdue_start_date) + str(publish_date))

            items = {}
            items['entity_name'] = entity_name
            items['debt_type'] = debt_type
            items['coin_type'] = coin_type
            items['overdue_amount'] = overdue_amount if overdue_amount else None
            items['overdue_principal'] = overdue_principal.replace(',', '') if overdue_principal else None
            items['overdue_interest'] = overdue_interest
            items['disclosing_party'] = disclosing_party
            items['creditor_name'] = creditor_name
            items['overdue_start_date'] = overdue_start_date
            items['repay_schedule'] = repay_schedule
            items['repay_amount'] = repay_amount.replace(',', '') if repay_amount else None
            items['entity_type'] = entity_type
            items['national_standard_category'] = national_standard_category
            items['national_standard_big_class'] = national_standard_big_class
            items['national_standard_middle_class'] = national_standard_middle_class
            items['national_standard_little_class'] = national_standard_little_class
            items['region'] = region
            items['due_date'] = due_date
            items['publish_date'] = publish_date
            items['md5_value'] = md5_value
            # insert_data('debt_overdue', item)
            yield items
