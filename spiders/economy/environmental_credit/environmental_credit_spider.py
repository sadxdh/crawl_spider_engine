"""环保信用评价 → entity_credithb
数据来源：221.10.90.154:8085 环保信用评价系统
"""
import hashlib, json, scrapy
from spiders.base_spider import BaseSpider
from utils.mysql_tools import select_data
from utils.time_kit import return_yesterday
from utils.tools import *


class EnvironmentCreditSpider(BaseSpider):
    name = 'economy_environmental_credit'
    data_table = 'entity_credithb'
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
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Content-Type': 'application/json;charset=UTF-8',
        'Referer': 'http://mee.net.cn/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
    }

    list_url = 'http://221.10.90.154:8085/eca/ComAppraise/SimpleQuery'
    from_data = {
        "YearNum": str(return_yesterday().year - 1),
        "RegionName": "",
        "Shengping": "",
        "CompanyName": "",
        "OrgCode": "",
        "Certificate": "",
        "StartIndex": 0,
        "Page": 1,
        "Rows": 1000,
        "Order": "desc",
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            json_data = self.from_data.copy()
            json_data['Page'] = page

            yield scrapy.http.JsonRequest(
                url=self.list_url,
                method='POST',
                headers=self.headers,
                data=json_data,
                callback=self.parse_list,
                dont_filter=True,
            )
    def parse_list(self, response):
        """列表解析"""
        result = response.json()
        datas = result['ResultObj']['Data']
        for data in datas:
            entity_name = data['CompanyName']
            evaluation_annual = data['YearNum']
            evaluation_area = data['RegionName']
            entity_code = data['OrgCode']
            evaluation_criterion = data['MethonNumber']
            announced_units = data['Remark']
            data_source = '环保信用中国-官网'
            evaluation_result = data['Shengping']
            md5_value = hash_md5(entity_name + str(evaluation_annual) + evaluation_result)

            items = {}
            items['md5_value'] = md5_value
            items['entity_name'] = entity_name
            items['entity_number'] = None
            items['grade'] = None
            items['evaluation_annual'] = evaluation_annual
            items['evaluation_area'] = evaluation_area
            items['entity_code'] = entity_code
            items['evaluation_criterion'] = evaluation_criterion
            items['announced_units'] = announced_units
            items['data_source'] = data_source
            items['evaluation_result'] = evaluation_result
            # insert_data(table='entity_credithb', data=item)
            yield items


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
