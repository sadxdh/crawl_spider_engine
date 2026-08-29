import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.mysql_tools import select_data
from utils.tools import *
from utils.time_kit import *
from scrapy.http import JsonRequest

class CompanyReportSzseSpider(BaseSpider):
    name = 'company_report_szse_spider'
    data_table = 'entity_announcement'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://www.szse.cn/disclosure/listed/notice/index.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0',
        'X-Requested-With': 'XMLHttpRequest',
    }
    domain = 'https://disc.static.szse.cn'
    base_url = 'https://www.szse.cn/api/disc/announcement/annList'
    category_url = 'https://www.szse.cn/api/disc/announcement/searchQuery'

    @staticmethod
    def get_security_code():
        datas = select_data(table='listing_info', data=['share_code'], condition='listed_exchange="深圳证券交易所"')
        return datas

    @staticmethod
    def generate_data(cate_value, page, security_code):
        json_data = {
            'seDate': ['', ''],
            'channelCode': ['listedNotice_disc'],
            'bigCategoryId': [cate_value],
            'pageSize': 50,
            'pageNum': page,
            'stock': [security_code]
        }
        return json_data

    @staticmethod
    def generate_params(cate_value, page):
        json_data = {
            'seDate': ['2025-04-01', ''],
            'channelCode': ['listedNotice_disc'],
            'bigCategoryId': [cate_value],
            'pageSize': 50,
            'pageNum': page,
        }
        return json_data

    def start_requests(self):
        params = {'random': str(random.random()), 'annType': 'szse'}
        separator = '&' if '?' in self.category_url else '?'
        request_url = f'{self.category_url}{separator}{urlencode(params)}'
        yield scrapy.Request(
            url=request_url,
            method='GET',
            headers=self.headers,
            callback=self.get_cate_type,
            dont_filter=True,
        )

    def get_cate_type(self, response):
        if response:
            category_info = response.json()['categoryInfo']
            for category in category_info:
                cate_name = category['text']
                cate_value = category['value']
                for page in range(self.start_page, self.end_page + 1):
                    json_data = self.generate_params(cate_value, page)
                    params = {
                        'random': str(random.random()),
                    }
                    separator = '&' if '?' in self.base_url else '?'
                    request_url = f'{self.base_url}{separator}{urlencode(params)}'
                    yield JsonRequest(
                        url=request_url,
                        method='POST',
                        headers=self.headers,
                        data=json_data,
                        callback=self.parse_list,
                        cb_kwargs={'cate_name': cate_name},
                        dont_filter=True,
                    )

    def parse_list(self, response, cate_name):
        response_json = response.json()
        result = response_json.get('data')
        if result:
            for row in result:
                publish_time = row['publishTime']
                announcement_title = row['title']
                href = row['attachPath']
                announcement_url = urljoin(self.domain, href)
                security_code = row['secCode'][0]
                security_short = row['secName'][0]

                source = '深交所'
                md5_value = hash_md5(str(publish_time)+announcement_title+security_code)

                items = {}
                items['publish_time'] = publish_time
                items['announcement_title'] = announcement_title
                items['announcement_url'] = announcement_url
                items['announcement_type'] = cate_name
                items['security_code'] = security_code
                items['security_short'] = security_short
                items['source'] = source
                items['md5_value'] = md5_value
                # insert_data(table='entity_announcement', data=item)
                yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')