"""
企业预警通 — 债券发行爬虫
数据来源：https://www.qyyjt.cn/bond/bondRelated/issuanceList
API：POST https://www.qyyjt.cn/finchinaAPP/v1/finchina-bond/v1/bond/issuance/listIssueDetail/v2

增量策略：
  - 分两轮：issue_status=1（已发行）、issue_status=2（未发行）
  - 每页50条
  - 增量：start_page=1 end_page=2（最新100条 × 2状态）
  - 去重字段：md5_value（bond_code + issue_date 的 md5）

本地调试：
  scrapy crawl finance_qyyjt_bond_issue -a start_page=1 -a end_page=2
"""
import scrapy
from spiders.finance.qyyjt.qyyjt_base_spider import QyyjtBaseSpider
from utils.tools import *
from datetime import datetime


class QyyjtBondIssueSpider(QyyjtBaseSpider):
    """企业预警通债券发行爬虫"""

    name = 'finance_qyyjt_bond_issue'
    data_table = 'bond_issue'
    dedup_fields = ['md5_value']

    custom_settings = {
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 3,
        'DEFAULT_REQUEST_HEADERS': {},
    }

    headers = {
        'accept': 'application/json',
        'accept-language': 'zh-CN,zh;q=0.9',
        'client': 'pc-web;pro',
        'content-type': 'application/json; charset=UTF-8',
        'origin': 'https://www.qyyjt.cn',
        'referer': 'https://www.qyyjt.cn/bond/bondRelated/issuanceList',
        'system1': 'Windows NT 10.0; Win64; x64;Chrome;139.0.0.0',
        'terminal': 'pc-web;pro',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
        'ver': '20250813',
        'x-request-id': 'zymDAUl9rdkHirUk5_4IB',
        'x-request-url': '%2Fbond%2FbondRelated%2FissuanceList',
    }

    @staticmethod
    def _build_body(skip: int, issue_status: int) -> dict:
        return {
            'type': '', 'area': '', 'debtRating': '', 'industry': '',
            'issueStartDate': '', 'issueEndDate': '', 'cityInvestment': '',
            'isPerpetual': '', 'sort': 'issueStartDate:desc',
            'firstType': '', 'secondType': '', 'subjectRating': '',
            'size': 50, 'from': skip, 'issuancePeriod': '',
            'keyword': '', 'enterpriseNature': '',
            'issueStatus': str(issue_status),
            'market': '', 'couponRate': '', 'expirationStartDate': '',
            'expirationEndDate': '', 'subId': '', 'isRight': '',
            'interestcalMethod': '', 'greenBond': '', 'conceptBond': '',
            'keywordScope': '', 'pubStatus': '', 'provinceCode': '',
            'cityCode': '', 'countyCode': '', 'crossMarket': '',
            'mergeCrossMarket': '', 'initialBondIssue': '',
            'raiseMethod': '', 'bondClassification': '', 'fiveArticles': '',
        }

    def start_requests(self):
        for issue_status in (1, 2):
            for page in range(self.start_page, self.end_page + 1):
                skip = self.page_to_skip(page)
                headers = self._get_auth_headers(self.headers)
                if not headers:
                    self.log_warning(f'status={issue_status} 第 {page} 页无 token，跳过')
                    continue
                body = self._build_body(skip, issue_status)
                yield scrapy.Request(
                    url='https://www.qyyjt.cn/finchinaAPP/v1/finchina-bond/v1/bond/issuance/listIssueDetail/v2',
                    method='POST',
                    headers=headers,
                    body=json.dumps(body),
                    callback=self.parse_list,
                    errback=self.errback,
                    meta={'page': page, 'issue_status': issue_status},
                    dont_filter=True,
                )

    def parse_list(self, response):
        result = response.json()['data']['list']
        for res in result:
            bond_code = res['bondCode']
            bond_abbr = res['bondAbbreviation']
            bond_name = res['bondFullName']
            issue_date = res['reportDate']

            issuer = res['issuerName']
            issue_start_date = res['issueStartDate']
            if issue_start_date > self.return_today('%Y-%m-%d'):
                continue
            items = {}
            items['md5_value'] = hash_md5(bond_code + issue_date)
            # item.spider_name = self.spider_name
            items['bond_code'] = bond_code
            items['bond_abbr'] = bond_abbr
            items['bond_name'] = bond_name
            items['bond_type'] = res['bondTypeName']
            items['sub_bond_type'] = res['secondType']
            items['issuer'] = issuer
            items['issue_date'] = issue_date
            items['plan_issue_scale'] = res['planIssuanceScale']
            items['actual_issue_scale'] = res['actualIssuanceScale']
            items['coupon_rate'] = res['couponRate']
            items['issue_rate'] = res['issuingRate']
            items['issue_reference_rate'] = res['referenceRate']
            items['entity_rating'] = res['subjectRating']
            items['rating_org'] = res['subjectRatingAgency']
            items['debt_rating'] = res['debtRating']
            items['debt_rating_org'] = res['debtRatingAgency']
            items['tender_upper_limit'] = res['tenderUpLimit']
            items['tender_lower_limit'] = res['tenderLowerLimit']
            items['bond_duration'] = res['yearBondMaturity']
            items['issue_duration'] = res['issuancePeriod']
            items['bond_with_embedded_options'] = res['entitlementType']
            items['raise_method'] = res['raiseMethod']
            items['issue_start_date'] = res['issueStartDate']
            items['issue_end_date'] = res['issueEndDate']
            items['issue_status'] = res['issueStatus']
            items['tender_method'] = res['tenderMethod']
            items['tender_subject'] = res['biddingSubject']
            items['tender_date'] = res['tenderDate']
            items['tender_time'] = res['biddingTime']
            items['payment_date'] = res['paymentDate']
            items['interest_calculate_method'] = res['calculationMethod']
            items['interest_payment_method'] = res['paymentMethod']
            items['interest_accrual_date'] = res['startInterestDate']
            items['interest_payment_date'] = res['payInterestDate']
            items['maturity_date'] = res['dueDate']
            items['listing_date'] = res['listingDate']
            items['listing_market'] = res['listedMarket']
            items['listing_platform'] = res['listingPlat']
            items['listing_price'] = res['issuingPrice']
            items['face_value'] = res['faceValue']
            items['benchmark_interest_rate'] = res['floatingInterestRate']
            items['entity_type'] = res['issuerEconomicNature']
            items['sw_level_one_industry'] = res['industryName']
            items['province'] = res['provinceName']
            items['city'] = res['cityName']
            items['district'] = res['districtName']
            items['location'] = res['attribution']
            items['actual_controller'] = res['actualController']
            items['is_guarantee'] = res['isGuarantee']
            items['guarantor'] = res['guaranteeName']
            items['guarantor_rating'] = res['guaranteeSubjectRating']
            items['lead_underwriter'] = res['leadUnderwriter']
            items['deputy_lead_underwriter'] = ''
            items['bond_servicer'] = res['survivalManageOrg']
            items['use_of_proceeds'] = res['raiseFundUse']
            items['booking_manager'] = res['bookkeeper']
            items['distributor'] = res['distributor']  # 分销商
            # insert_data('bond_issue', item)
            yield items

    def return_today(self, date_type):
        """返回今天日期"""
        return datetime.today().strftime(date_type)
