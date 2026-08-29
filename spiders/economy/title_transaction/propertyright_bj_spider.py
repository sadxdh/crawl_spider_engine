"""北京产权交易 → entity_propertyright_transaction
参照旧项目 bj_title_spider（原项目使用 JSL 521 绕过，现用 CurlCffiMiddleware）
"""
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.economy.title_transaction.common_function import query_entity_id
from utils.tools import *


class PropertyRightBJSpider(BaseSpider):
    name = 'economy_propertyright_bj'
    data_table = 'entity_propertyright_transaction'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'


    jsl_url = 'https://www.cbex.com.cn/xm/cqzr/zspl/'
    base_url = 'https://www.cbex.com.cn/onss-api/jsonp/project/search'

    @staticmethod
    def generate_params(page, property_type):
        params = {
            'fromPage': page,
            'pageSize': '15',
            'businessType': 'JC',
            'disclosureType': property_type,
            'sortProperty': 'disclosuretime',
            'sortDirection': '1',
            'mark': 'xm'}
        return params

    def start_requests(self):
        for property_type in ('G3', 'PG3'):
            for page in range(self.start_page, self.end_page + 1):
                params = self.generate_params(page, property_type)
                url = f'{self.base_url}?{urlencode(params)}'
                response = get_jsl_cookies(url=url, proxies_type=True)
                property_type_cn = '预披露' if 'PG3' in params['disclosureType'] else '正式披露'
                yield from self.parse_list(response, property_type_cn)

    def parse_list(self, response, property_type):
        result = response.json()
        datas = result['data']['data']
        for data in datas:
            project_code = data['code']
            project_name = data['name']
            file_url = data.get('docsurl')
            listing_price = data['disclosureprice']
            disclose_start_date = data.get('disclosuretime')
            disclose_end_date = data.get('disclosureendtime')
            disclose_end_date = disclose_end_date if disclose_end_date else None
            transaction_type = data['businesstypename']
            industry_name = data['industryname']
            transferor = data.get('sellername')
            transferee = data.get('objectname')
            region = data['regionname']
            authorize_unit = data.get('authorizeunit')
            manage_department = data.get('hqname')
            md5_value = hash_md5(project_code + str(listing_price) + str(disclose_start_date))

            items = {}
            items['project_code'] = project_code
            items['project_name'] = project_name
            items['file_url'] = file_url
            items['listing_price'] = listing_price
            items['disclose_start_date'] = disclose_start_date
            items['disclose_end_date'] = disclose_end_date
            items['transaction_type'] = transaction_type
            items['industry_name'] = industry_name
            items['transferor'] = transferor
            items['transferee_id'] = query_entity_id(transferee)
            items['transferee'] = transferee
            items['region'] = region
            items['authorize_unit'] = authorize_unit
            items['manage_department'] = manage_department
            items['property_right_status'] = property_type
            items['source'] = '北京产权交易所'
            items['md5_value'] = md5_value
            # insert_data(table='entity_propertyright_transaction', data=item)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
