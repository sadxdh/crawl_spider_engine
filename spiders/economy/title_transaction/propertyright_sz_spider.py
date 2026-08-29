"""深圳产权交易 → entity_propertyright_transaction
参照旧项目 shenzhen_title_spider.py
"""
from urllib.parse import urlencode
import scrapy
from spiders.base_spider import BaseSpider
from spiders.economy.title_transaction.common_function import query_entity_id
from utils.tools import *


class PropertyRightSZSpider(BaseSpider):
    name = 'economy_propertyright_sz'
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
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'content-type': 'application/json',
        'origin': 'https://www.sotcbb.com',
        'referer': 'https://www.sotcbb.com/xmgg?id=xmggcqzrzspl',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
    }
    base_url = 'https://www.sotcbb.com/api/v1/sotcbb/local/project/list'
    view_url = 'https://www.sotcbb.com/cqjy-api/package/view'

    def generate_params(self, page):
        json_data = {
            'channelIds': ['3226',],
            'projectMoneyRanges': [],
            'projectSubjections': [],
            'projectSources': [],
            'projectStatus': None,
            'releaseTimeBegin': None,
            'releaseTimeEnd': None,
            'title': None,
            'pageNum': page,
            'pageSize': 10,
            'dataType': 1,
            'targetColumnIds': ['3961',],
        }
        return json_data

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            data = self.generate_params(page)
            yield scrapy.http.JsonRequest(
                url=self.base_url,
                method='POST',
                headers=self.headers,
                data=data,
                callback=self.parse_list,
                dont_filter=True,
            )

    def parse_list(self, response):
        result = response.json()
        datas = result['data']['content']
        for data in datas:
            project_name = data['title']
            property_right_status = data['projectType']
            transaction_type = data['projectBusiness']

            object_id = data['objectId']
            channel_id = data['channelId']
            content_id = data['contentId']
            file_url = f'https://www.sotcbb.com/bdDetail.htm?contentId={object_id}&channelId={channel_id}&id={content_id}'

            temp = {
                'project_name': project_name,
                'property_right_status': property_right_status,
                'transaction_type': transaction_type,
                'file_url': file_url,
                'object_id': object_id,
            }
            params = {
                'id': object_id,
            }
            separator = '&' if '?' in self.view_url else '?'
            request_url = f'{self.view_url}{separator}{urlencode(params)}'
            yield scrapy.http.JsonRequest(
                url=request_url,
                method='POST',
                headers=self.headers,
                data={},
                callback=self.parse_view,
                cb_kwargs={'list_data': temp},
                dont_filter=True,
            )

    def parse_view(self, response, list_data):
        result = response.json()
        data = result['data']

        if data:
            res = data['portalTPackage']
            listing_price = res['listingTotalPrice']  # 元
            disclose_start_date = res.get('listingStartTime')
            disclose_end_date = res.get('listingEndTime')

            (project_code, region, industry_name, transferor, transferee, authorize_unit,
             manage_department) = None, None, None, None, None, None, None

            form = result['data']['form']
            if form:
                for section in form:
                    value = section['value']
                    for subsection in value:
                        subname = subsection['name']
                        if '项目编号' in subname:
                            project_code = subsection['value']
                        if '所在地区' in subname:
                            region = subsection['value']
                        if '所属行业' in subname:
                            industry_name = subsection['value']
                        if '标的企业名称' in subname:
                            transferee = subsection['value']
                        if '转让方名称' in subname:
                            transferor = subsection['value']
                        if '批准单位名称' in subname:
                            authorize_unit = subsection['value']
                        if '主管部门名称' in subname:
                            manage_department = subsection['value']
                            if not manage_department:
                                manage_department = authorize_unit

            project_name = list_data['project_name']
            # 没有form的情况下解析项目名称中的编号
            if not project_code:
                project_code = re.findall(r"编号([^)]+)", project_name)[0]

            # 挂牌价单位元，转换为万元
            listing_price =  int(listing_price) / 10000 if listing_price else None
            md5_value = hash_md5(project_code + str(listing_price) + str(disclose_start_date))

            items = {}
            items['project_code'] = project_code
            items['project_name'] = project_name
            items['file_url'] = list_data['file_url']
            items['listing_price'] = str(listing_price)
            items['disclose_start_date'] = disclose_start_date
            items['disclose_end_date'] = disclose_end_date
            items['transaction_type'] = list_data['transaction_type']
            items['industry_name'] = industry_name
            items['transferor'] = transferor
            items['transferee_id'] = query_entity_id(transferee)
            items['transferee'] = transferee
            items['region'] = region
            items['authorize_unit'] = authorize_unit
            items['manage_department'] = manage_department
            items['property_right_status'] = list_data['property_right_status']
            items['source'] = '深圳联合产权交易所'
            items['md5_value'] = md5_value
            # insert_data(table='entity_propertyright_transaction', data=item)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
