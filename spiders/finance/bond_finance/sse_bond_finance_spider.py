import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class BondFinanceSseSpider(BaseSpider):
    name = 'bond_finance_sse'
    data_table = 'entity_bond_finance'
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
        'Referer': 'https://www.sse.com.cn/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0',
        'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Microsoft Edge";v="128"',
    }

    base_url = 'https://query.sse.com.cn/sseQuery/commonSoaQuery.do'
    bond_type_list = [
        {'bond_type': '记账式国债', 'pages': 49},
        {'bond_type': '地方政府债券', 'pages': 545},
        {'bond_type': '金融债', 'pages': 2},
        {'bond_type': '企业债券,公司债券,新企业债券', 'pages': 653},
        {'bond_type': '中小企业私募债券,非公开发行公司债券', 'pages': 802},
        {'bond_type': '可转换公司债券', 'pages': 10},
        {'bond_type': '分离交易的可转换公司债券', 'pages': 1},
        {'bond_type': '可交换公司债券', 'pages': 9},
        {'bond_type': '次级债券', 'pages': 13},
        {'bond_type': '证券公司资产支持证券', 'pages': 781},
        {'bond_type': '信贷资产支持证券', 'pages': 1},
    ]

    @staticmethod
    def generate_params(bond_type, page):
        params = {
            'isPagination': 'true',
            'pageHelp.pageSize': '25',
            'pageHelp.pageNo': page,
            'pageHelp.beginPage': page,
            'pageHelp.cacheSize': '1',
            'pageHelp.endPage': page,
            'sqlId': 'CP_ZQ_ZQLB',
            'BOND_CODE': '',
            'BOND_TYPE': bond_type,
        }
        return params

    def start_requests(self):
        for types in self.bond_type_list:
            bond_type = types['bond_type']
            count_page = types['pages']
            end_pages = count_page if self.end_page > 999 else self.end_page
            for page in range(self.start_page, int(end_pages) + 1):
                params = self.generate_params(bond_type, page)
                separator = '&' if '?' in self.base_url else '?'
                request_url = f'{self.base_url}{separator}{urlencode(params)}'
                yield scrapy.Request(
                    url=request_url,
                    method='GET',
                    headers=self.headers,
                    callback=self.parse_list,
                    dont_filter=True,
                    cb_kwargs={'bond_type': bond_type}
                )

    def parse_list(self, response, bond_type):
        result = json.loads(response.text)
        datas = result['result']
        if datas:
            for data in datas:
                bond_code = data['BOND_CODE']
                params = {
                    'isPagination': 'false',
                    'sqlId': 'CP_ZQ_ZQLB',
                    'BOND_CODE': bond_code,
                    'BOND_TYPE': bond_type,
                }
                separator = '&' if '?' in self.base_url else '?'
                request_url = f'{self.base_url}{separator}{urlencode(params)}'

                yield scrapy.Request(
                    url=request_url,
                    method='GET',
                    headers=self.headers,
                    callback=self.parse_detail,
                    cb_kwargs={'bond_type': bond_type},
                    dont_filter=True,
                )

    def parse_detail(self, response, bond_type):
        result = response.json()['result']
        for data in result:
            bond_code = data['BOND_CODE']
            bond_short_name = data['BOND_ABBR']
            bond_expand_short_name = data['SECURITY_ABBR_FULL']
            bond_full_name = data['BOND_FULL']
            calculate_mode = data['INTEREST_TYPE']
            pay_mode = data['PAY_TYPE']
            issue_volume = data['ISSUE_VALUE_HM']
            listing_date = data['LISTING_DATE']
            issue_term = data['TERM_YEAR']
            issue_date = data['ONLINE_START_DATE']
            issue_end_date = data['ONLINE_END_DATE']
            issue_owner = data['ISSUE_OWNER']
            issue_price = data['ISSUE_PRICE']
            is_guarantee = data['IS_NOT_DB']
            issue_face_rate = data['FACE_RATE']
            issue_face_value = data['FACE_VALUE']
            due_date = data['END_DATE']
            md5_value = hash_md5(bond_code+listing_date)

            if '企业债券' in bond_type:
                bond_type = '公开发行公司债券（含企业债券）'
            elif '中小企业私募债券' in bond_type:
                bond_type = '非公开发行公司债券（含企业债券）'

            items = {}
            items['bond_code'] = bond_code
            items['bond_short_name'] = bond_short_name
            items['bond_expand_short_name'] = bond_expand_short_name
            items['bond_full_name'] = bond_full_name
            items['bond_type'] = bond_type
            items['interest_calculate_mode'] = calculate_mode
            items['interest_pay_mode'] = pay_mode
            items['bond_issue_volume'] = issue_volume
            items['listing_date'] = listing_date
            items['issue_date'] = self.handle_value(issue_date)
            items['issue_end_date'] = self.handle_value(issue_end_date)
            items['due_date'] = due_date
            items['issue_term'] = issue_term
            items['issue_owner'] = issue_owner
            items['issue_price'] = self.handle_value(issue_price)
            items['issue_face_rate'] = issue_face_rate
            items['issue_face_value'] = issue_face_value
            items['is_guarantee'] = is_guarantee
            items['md5_value'] = md5_value
            # insert_data('entity_bond_finance', item)
            yield items

    @staticmethod
    def handle_value(value):
        value = None if value == '-' else value
        return value

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')