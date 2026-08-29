"""
企业预警通 — 债券违约大全爬虫
数据来源：https://www.qyyjt.cn/default/bondDefault/full/bond
API：POST https://www.qyyjt.cn/getData.action?_t=765

增量策略：
  - 每页50条，按更新时间降序
  - 增量：start_page=1 end_page=2（最新100条）
  - 去重字段：md5_value（bond_code + issuer 的 md5）

本地调试：
  scrapy crawl finance_qyyjt_bond_default -a start_page=1 -a end_page=2
"""
import scrapy
from utils.tools import *
from spiders.finance.qyyjt.qyyjt_base_spider import QyyjtBaseSpider


class QyyjtBondDefaultSpider(QyyjtBaseSpider):
    """企业预警通债券违约大全爬虫"""

    name = 'finance_qyyjt_bond_default'
    data_table = 'bond_default'
    dedup_fields = ['md5_value']

    custom_settings = {
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 3,
        'DEFAULT_REQUEST_HEADERS': {},  # 动态注入，不用全局覆盖
    }

    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cache-control': 'no-cache',
        'client': 'pc-web;pro',
        'dataid': '765',
        'origin': 'https://www.qyyjt.cn',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://www.qyyjt.cn/default/bondDefault/full/bond',
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
    base_url = 'https://www.qyyjt.cn/getData.action'

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            skip = self.page_to_skip(page)
            headers = self._get_auth_headers(self.headers)
            if not headers:
                self.log_warning(f'第 {page} 页无 token，跳过')
                continue
            yield scrapy.Request(
                url=self.base_url,
                method='POST',
                headers=headers,
                body=f'skip={skip}&pagesize=50&_t=765',
                callback=self.parse_list,
                errback=self.errback,
                dont_filter=True,
            )

    def parse_list(self, response):
        result = response.json()['data']['list']
        for data in result:
            bond_code = data['bondCode']
            bond_abbr = data['shortName']
            bond_type = data.get('bondType')
            listed_market = data.get('Exchange')
            total_default_amount = data.get('allAmount')
            latest_default_amount = data.get('amount')
            latest_default_type = data.get('cashflowType')
            latest_default_reason = data.get('reason')
            latest_default_date = data.get('latestDate')
            first_default_date = data.get('firstDate')
            total_repay_amount = data.get('accumRepayAmount')
            repay_schedule = data.get('repayProcess')
            grace_period = data.get('gracePriod')
            credit_enhance_measure = data.get('creditEnhanceStep')
            disposal_concept = data.get('handleWay')
            issuer = data.get('orgName')
            entity_type = data.get('enterpriseProperty')
            industry = data.get('industry')
            region = data.get('area')
            latest_entity_rating = data.get('entityRating')
            lead_underwriter = data.get('underwriter')
            md5_value = hash_md5(bond_code + issuer)

            total_repay_amount = self.convert_billion_to_zero(total_repay_amount)

            items = {}
            items['bond_code'] = bond_code
            items['bond_abbr'] = bond_abbr
            items['bond_type'] = bond_type
            items['listed_market'] = listed_market
            items['total_default_amount'] = total_default_amount
            items['latest_default_amount'] = latest_default_amount
            items['latest_default_type'] = latest_default_type
            items['latest_default_reason'] = latest_default_reason
            items['latest_default_date'] = latest_default_date
            items['first_default_date'] = first_default_date
            items['total_repay_amount'] = total_repay_amount
            items['repay_schedule'] = repay_schedule
            items['grace_period'] = grace_period
            items['credit_enhance_measure'] = credit_enhance_measure
            items['disposal_concept'] = disposal_concept
            items['issuer'] = issuer
            items['entity_type'] = entity_type
            items['industry'] = industry
            items['region'] = region
            items['latest_entity_rating'] = latest_entity_rating
            items['lead_underwriter'] = lead_underwriter
            items['md5_value'] = md5_value
            # insert_data('bond_default', item)
            yield items

    @staticmethod
    def convert_billion_to_zero(value):
        if not value:
            return None
        # 去掉“亿”字
        num_str = value.replace("亿", "")
        # 转换为浮点数
        num_float = float(num_str)
        # 判断是否为 0
        if num_float == 0:
            return 0
        return num_float  # 如果不是 0，返回原值