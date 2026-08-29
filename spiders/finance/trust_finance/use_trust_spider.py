import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *


# data_crawl_server   spider/finance/trust_finance/use_trust_spider.py
class TrustFinanceUseTrustSpider(BaseSpider):
    name = 'trust_finance_use_trust'
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
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://www.yanglee.com/Product/?producttype=%E4%BF%A1%E6%89%98%E4%BA%A7%E5%93%81',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0',
        'X-Requested-With': 'XMLHttpRequest',
    }

    base_url = 'https://www.yanglee.com/Action/ProductAJAX.ashx'
    detail_url = 'https://www.yanglee.com/Product/Detail.aspx?id={}'

    @staticmethod
    def generate_params(page):
        params = {
            'mode': 'statistics',
            'pageSize': '40',
            'pageIndex': page,
            'conditionStr': 'producttype:1',
            'start_released': '',
            'end_released': '',
            'orderStr': '1',
            'ascStr': 'uldow',
        }
        return params

    def start_requests(self):
        for page in range(int(self.start_page), int(self.end_page) + 1):
            params = self.generate_params(page)
            req_url = f"{self.base_url}?{urlencode(params)}"
            yield scrapy.Request(
                url=req_url,
                method="GET",
                headers=self.headers,
                callback=self.parse_list
            )

    def parse_list(self, response):
        result = response.json()['result']
        for data in result:
            detail_id = data['ID']
            req_url = self.detail_url.format(detail_id)
            yield scrapy.Request(
                url=req_url,
                method="GET",
                headers=self.headers,
                callback=self.parse_detail
            )

    def parse_detail(self, response):
        result = etree.HTML(response.text)
        credit_enhancement = self.handle_xpath_result(result.xpath('//div[@id="t6"]/p/text()'))
        funds_purpose = self.handle_xpath_result(result.xpath('//div[@id="t4"]/p/text()'))

        tr_list = result.xpath('//table[contains(@class,"maintab")]//tr')
        temp = {
            'project_name': '产品名称',
            'issue_scale': '发行规模',
            'issue_date': '发行时间',
            'mini_investment_amount': '投资门槛',
            'issue_owner': '发行机构',
            'investment_term': '产品期限',
            'trust_status': '产品状态',
            'yield_type': '收益类型',
            'investment_direction': '投资领域',
        }
        data = {}
        for key, value in temp.items():
            for tr in tr_list:
                last_name = tr.xpath(f'./td[text()="{value}"]/text()')
                if last_name:
                    parse_value = tr.xpath(f'./td[text()="{value}"]/following-sibling::td[1]/text()')
                    if parse_value:
                        res = parse_value[0]
                        data[key] = res
        data['credit_enhancement'] = credit_enhancement
        data['funds_purpose'] = funds_purpose
        # return data
        yield from self.save_data(data)

    def save_data(self, data):
        mini_investment_amount = match_text(data['mini_investment_amount'], r'\d+')
        issue_date = match_text(data['issue_date'], r'(\d{4}-\d{2}-\d{2}).*至')
        issue_date = issue_date if issue_date else None
        md5_value = hash_md5(data['project_name'] + issue_date if issue_date else '')

        items = {}
        # item.spider_name = self.spider_name
        items['project_name'] = data['project_name']
        items['issue_scale'] = match_text(data['issue_scale'], pattern=r'\d+')
        items['issue_date'] = issue_date
        items['mini_investment_amount'] = mini_investment_amount
        items['investment_term'] = data['investment_term']
        items['trust_status'] = data.get('trust_status')
        items['issue_owner'] = data.get('issue_owner')
        items['funds_purpose'] = data.get('funds_purpose')
        items['credit_enhancement'] = data.get('credit_enhancement')
        items['yield_type'] = data.get('yield_type')
        items['investment_direction'] = data.get('investment_direction')
        items['md5_value'] = md5_value
        items['source'] = '用益信托网'
        # insert_data('entity_trust_finance', item)
        yield items


    @staticmethod
    def handle_xpath_result(result):
        return result[0] if result else None


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')