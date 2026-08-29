"""
中诚信国际（CCXI）信用评级爬虫
数据来源：https://www.ccxi.com.cn
API：GET https://website-api.ccxi.com.cn/admin/content/cspj/page

评级类型：
  企业评级=74  金融机构评级=75  结构融资评级=77
  地方政府债=78  熊猫债=79  定期跟踪=104

增量策略：
  - 每页1000条（接口支持大分页）
  - 增量：start_page=1 end_page=1
  - 去重字段：md5_value（issuer_name + rating_date 的 md5）

本地调试：
  scrapy crawl economy_ccxi_credit_rating -a start_page=1 -a end_page=1
"""

from urllib.parse import urlencode
import scrapy
from spiders.base_spider import BaseSpider
from utils.mysql_tools import select_data
from utils.tools import *


class CCXICreditRatingSpider(BaseSpider):
    """中诚信国际信用评级爬虫"""
    name = 'economy_ccxi_credit_rating'
    data_table = 'entity_credit_rating'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,'
                  'image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/126.0.0.0 Safari/537.36',
    }
    base_url = 'https://website-api.ccxi.com.cn/admin/content/cspj/page'

    rating_type = {
        "企业评级": 74,
        "金融机构评级": 75,
        "结构融资评级": 77,
        "地方政府债": 78,
        "熊猫债": 79,
        "定期跟踪": 104
    }

    @staticmethod
    def generate_params(page, *args):
        level = args[0]
        params = {
            'codetranslate': 'true',
            'filters': '{"launchedstatus": "启用", "levelone": "73", "leveltwo": "%s"}' % level,
            'orderby': '{"rankdate": "desc"}',
            'pageNo': page,
            'pageSize': 1000
        }
        return params

    def start_requests(self):
        for type_key, type_value in self.rating_type.items():
            for page in range(self.start_page, self.end_page + 1):
                params = self.generate_params(page, type_value)
                query_string = urlencode(params)
                url = urljoin(self.base_url, '?' + query_string)
                yield scrapy.Request(
                    url=url,
                    headers=self.headers,
                    callback=self.parse_list
                )

    def parse_list(self, response):
        result = response.json()
        rows = result['data']['records']
        for row in rows:
            detail_id = row['id']
            detail_url = f'https://www.ccxi.com.cn/creditrating/result/InitialRating/detail/{detail_id}'

            project_name = row.get('bondname')
            level_three = row.get('levelthreech')
            if level_three == '主体评级':
                project_name = None

            issuer_name = row['issuers']
            entity_name = match_text(issuer_name, r'(.*?公司|银行)')
            entity_id = self.query_entity_code(entity_name)

            rating_date = row['rankdate']
            entity_rating = row.get('subjectlevel')
            rating_outlook = row.get('expectation')
            debt_rating = row.get('debtlevel')
            announcement_url = row.get('subjectreport')

            if issuer_name and rating_date:
                md5_value = hash_md5(issuer_name + str(rating_date))
                items = {}
                items['md5_value'] = md5_value
                items['entity_id'] = entity_id
                items['entity_name'] = entity_name
                items['project_name'] = project_name
                items['rating_date'] = rating_date
                items['entity_rating'] = entity_rating
                items['rating_outlook'] = rating_outlook
                items['debt_rating'] = debt_rating
                items['rating_agency'] = '中诚信国际信用评级有限责任公司'
                items['url'] = detail_url
                items['announcement_title'] = entity_name
                items['announcement_url'] = announcement_url
                # insert_data(table='entity_credit_rating', data=item)
                yield items

    def query_entity_code(self, entity_name):
        if entity_name is None:
            return None
        mysql_result = select_data(table='wentao_basedata.entity_info',
                                   data=['entity_id'],
                                   condition=f'entity_name = "{entity_name}";')
        return mysql_result[0]['entity_id'] if mysql_result else None

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
