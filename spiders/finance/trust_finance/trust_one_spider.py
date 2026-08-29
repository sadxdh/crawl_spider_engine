import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *


# data_crawl_server  spider/finance/trust_finance/trust_one_spider.py
class TrustFinanceTrustOneSpider(BaseSpider):
    """信托网"""
    name = 'trust_finance_trust_one'
    data_table = 'entity_trust_finance'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://www.trust-one.com/product?abc=1&SPtype=1&DS=1&OL=0&feIndex=2',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0',
    }

    base_url = 'https://www.trust-one.com/api/search/product'

    def start_requests(self):
        for page in range(int(self.start_page), int(self.end_page) + 1):
            params = {'SPtype': '1', 'page': page, 'source': 'web'}
            req_url = f'{self.base_url}?{urlencode(params)}'
            yield scrapy.Request(
                url=req_url,
                method='GET',
                headers=self.headers,
                callback=self.parse_list
            )

    def parse_list(self, response):
        result = response.json()
        datas = result['list']
        for data in datas:
            trust_id = data['id']
            detail_url = f'https://www.trust-one.com/api/product/{trust_id}'

            project_name = data['name']
            issue_scale = int(data['maxLimit'])/10000
            issue_date = data['endDate']
            mini_investment_amount = data['minLimit']
            interest_pay_cycle = data['distribution']
            investment_term = data['time']
            performance_compare_benchmark = data['rate']
            trust_status = data['status']

            pre_datas = {
                'project_name': project_name,
                'issue_scale': issue_scale,
                'issue_date': issue_date,
                'mini_investment_amount': mini_investment_amount,
                'interest_pay_cycle': interest_pay_cycle,
                'investment_term': investment_term,
                'performance_compare_benchmark': performance_compare_benchmark,
                'trust_status': trust_status
            }
            # self.get_detail(detail_url, pre_datas)
            yield scrapy.Request(
                url=detail_url,
                method='GET',
                headers=self.headers,
                callback=self.parse_detail,
                cb_kwargs={'pre_datas': pre_datas}
            )

    def parse_detail(self, response, pre_datas):
        result = response.json()
        issue_owner = result['issuer']
        issue_full_owner = result['issuerFullName']
        funds_purpose = self.match_value(result['application'])
        credit_enhancement = self.match_value(result['riskControl'][0])
        yield_type = result['revenueType']
        investment_direction = result['investment']

        project_name = pre_datas['project_name']
        issue_date = pre_datas['issue_date']
        md5_value = hash_md5(project_name+issue_date)

        items = {}
        # item.spider_name = self.spider_name
        items['project_name'] = project_name
        items['issue_scale'] = pre_datas['issue_scale']
        items['issue_date'] = issue_date
        items['mini_investment_amount'] = pre_datas['mini_investment_amount']
        items['interest_pay_cycle'] = pre_datas['interest_pay_cycle']
        items['investment_term'] = pre_datas['investment_term']
        items['performance_compare_benchmark'] = pre_datas['performance_compare_benchmark']
        items['trust_status'] = pre_datas['trust_status']
        items['issue_owner'] = issue_owner
        items['issue_owner_full_name'] = issue_full_owner
        items['funds_purpose'] = funds_purpose
        items['credit_enhancement'] = credit_enhancement
        items['yield_type'] = yield_type
        items['investment_direction'] = investment_direction
        items['md5_value'] = md5_value
        items['source'] = '信托网'
        # insert_data('entity_trust_finance', item)
        yield items

    @staticmethod
    def match_value(value):
        if not value:
            return None
        result = re.findall(r'>(.*)<', value)
        return result[0] if result else None

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')