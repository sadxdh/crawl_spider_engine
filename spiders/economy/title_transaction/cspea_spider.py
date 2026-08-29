import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.economy.title_transaction.cspea_login import AccountLogin
from utils.db.redis_opt import hgetall
from utils.tools import *
from utils.time_kit import *

class TitleTransactionCspeaSpider(BaseSpider):
    name = 'title_transaction_cspea'
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
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://www.cspea.com.cn',
        'Referer': 'https://www.cspea.com.cn/list?c=C02&s=A02,A03',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
        'X-Requested-With': 'XMLHttpRequest',
    }
    COOKIE_REDIS_KEY = 'title_transaction:cookie_pool'
    list_url = 'https://www.cspea.com.cn/esApi/searchIndex'
    right_status = {'A01': '预披露', 'A02': '正式披露', 'A03': '正式披露', 'A06': '成交公示', 'A07': '成交公示'}
    cookie_status = False

    @staticmethod
    def generate_data(page):
        data = {
            'projectClassifyCode': 'C02',
            'businessStatus': 'A02,A03,A06,A07',
            'sortVal': 'publishDate',
            'sortRule': 'desc',
            'pageNum': str(page),
            'pageSize': '12',
        }
        return data

    def get_cookies(self):
        cookies_dict = hgetall(self.COOKIE_REDIS_KEY)
        if not cookies_dict or not self.cookie_status:
            cookies = AccountLogin().login()
            return cookies
        else:
            cookies = list(cookies_dict.values())[0]
            return json.loads(cookies)


    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            data = self.generate_data(page)
            cookies = self.get_cookies()
            yield scrapy.FormRequest(
                url=self.list_url,
                method='POST',
                headers=self.headers,
                cookies=cookies,
                formdata=data,
                callback=self.parse_list,
                dont_filter=True,
            )

    def parse_list(self, response):
        result = response.json()
        res = result['entity']
        if not res:
            self.cookie_status = False
        else:
            datas = res['datas']
            for data in datas:
                project_code = data['projectCode']
                project_name = data['projectName']
                file_url = f'https://bigdata.cspea.com.cn/cq/proj/{project_code}'
                listing_price = data['projectPrice']
                start_date = data.get('publishDate')
                end_date = data.get('expireDate')
                disclose_start_date = timestamp_to_datetime(start_date).date() if start_date else None
                disclose_end_date = timestamp_to_datetime(end_date).date() if end_date else None
                industry_name = data.get('industryName')
                transferor = data.get('sellerName')
                authorize_unit = data.get('hqName')

                property_right_status = data['businessStatus']
                property_right_status = self.right_status.get(property_right_status)


                md5_value = hash_md5(project_code + str(listing_price) + str(disclose_start_date))

                items = {}
                items['project_code'] = project_code
                items['project_name'] = project_name
                items['file_url'] = file_url
                items['listing_price'] = str(listing_price)
                items['disclose_start_date'] = disclose_start_date
                items['disclose_end_date'] = disclose_end_date
                items['transaction_type'] = '产权转让'
                items['industry_name'] = industry_name
                items['transferor'] = transferor
                items['authorize_unit'] = authorize_unit
                items['property_right_status'] = property_right_status
                items['source'] = '产投数据'
                items['md5_value'] = md5_value
                # insert_data(table='entity_propertyright_transaction', data=item)
                yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')