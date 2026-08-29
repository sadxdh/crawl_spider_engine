"""上海产权交易 → entity_propertyright_transaction
参照旧项目 sh_title_transaction_spider
"""
import scrapy
from urllib.parse import urlencode
from spiders.economy.title_transaction.common_function import query_entity_id
from utils.tools import *
from spiders.base_spider import BaseSpider


class PropertyRightSHSpider(BaseSpider):
    name = 'economy_propertyright_sh'
    data_table = 'entity_propertyright_transaction'
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
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://trade.suaee.com',
        'Referer': 'https://trade.suaee.com/TransactionPortal/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0',
    }
    list_url = 'https://trade.suaee.com/manageprojectweb/foreign/project/queryAllNew'
    detail_url = 'https://www.suaee.com/manageproject/foreign/projectPreview/getCQProjectPreview'

    @staticmethod
    def generate_data(page):
        json_data = {
            'projectType': 'CHANQUAN',
            'childProjectType': None,
            'ateTimesort': '1',
            'clickAmountsort': '1',
            'pageQuery': {'pageIndex': page, 'pageSize': 10},
        }
        return json_data

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            json_data = self.generate_data(page)
            yield scrapy.http.JsonRequest(
                url=self.list_url,
                method='POST',
                headers=self.headers,
                data=json_data,
                callback=self.parse_list,
                dont_filter=True,
            )

    def parse_list(self, response):
        result = response.json()
        datas = result['data']['data']
        for data in datas:
            detail_id = data['xmid']
            file_url = data['xmurl']
            industry_name = data['sshy']
            region = data.get('szdqs', '') + data.get('szdqsq', '') + data.get('szdqqx', '')
            temp = {'detail_id': detail_id, 'file_url': file_url, 'region': region, 'industryname': industry_name}
            params = {
                'xmid': detail_id,
                'gplx': '',
                'type': '',
                'imgType': '',
            }
            separator = '&' if '?' in self.detail_url else '?'
            request_url = f'{self.detail_url}{separator}{urlencode(params)}'
            yield scrapy.Request(
                url=request_url,
                method='GET',
                headers=self.headers,
                callback=self.parse_detail,
                cb_kwargs={'data_info': temp},
                dont_filter=True,
            )

    def parse_detail(self, response, data_info):
        result = response.json()
        data = result['data']

        project_code = data['xmbh']
        project_name = data['xmmc']
        listing_price = data.get('zrdj')
        disclose_start_date = data['plksrq']
        disclose_end_date = data['pljsrq']
        transferee = data['bdqymc']

        relate_party = data['zrfxx'][0]
        authorize_unit = relate_party.get('pzdwmc')
        manage_department = relate_party.get('ssjt')
        transferor = relate_party['zrfmc']

        property_right_status = '正式披露' if listing_price else '预披露'

        md5_value = hash_md5(project_code + str(disclose_start_date))
        items = {}
        items['project_code'] = project_code
        items['project_name'] = project_name
        items['file_url'] = data_info['file_url']
        items['listing_price'] = listing_price
        items['disclose_start_date'] = disclose_start_date
        items['disclose_end_date'] = disclose_end_date
        items['transaction_type'] = '股权转让'
        items['industry_name'] = data_info['industryname']
        items['transferor'] = transferor
        items['transferee_id'] = query_entity_id(transferee)
        items['transferee'] = transferee
        items['region'] = data_info['region']
        items['authorize_unit'] = authorize_unit
        items['manage_department'] = manage_department
        items['property_right_status'] = property_right_status
        items['source'] = '上海联合产权交易所'
        items['md5_value'] = md5_value
        # insert_data(table='entity_propertyright_transaction', data=item)
        yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
