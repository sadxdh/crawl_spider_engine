import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *


class BondFinanceBseSpider(BaseSpider):
    name = 'bond_finance_bse'
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
        'Accept': 'text/javascript, application/javascript, application/ecmascript, '
                  'application/x-ecmascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://www.bse.cn',
        'Referer': 'https://www.bse.cn/disclosure/xyznotice.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Microsoft Edge";v="128"',
        'sec-ch-ua-platform': '"Windows"',
    }

    base_url = 'https://www.bse.cn/disclosureInfoController/zoneInfoResult.do'
    detail_url = 'https://www.bse.cn/fipZqxxController/fipZqxxInfo.do'

    @staticmethod
    def generate_params(page):
        data = {
            'companyCd': '',
            'disclosureSubtypes[]': [
                '9602-0001',
                '9602-0002',
                '9602-0003',
                '9602-0004',
                '9602-0005',
                '9602-0006',
                '9602-0007',
                '9602-0008',
                '9602-0009',
                '9602-0010',
                '9602-0011',
                '9602-0012',
                '9602-0013',
                '9602-0301',
                '9603-0101',
                '9603-0102',
                '9603-0103',
                '9603-0104',
                '9603-0301',
                '9603-0302',
                '9603-0401',
                '9603-0402',
                '9603-0501',
                '9603-0502',
                '9603-0503',
                '9603-0504',
                '9603-0505',
                '9603-0601',
                '9603-0602',
                '9603-0603',
                '9603-0701',
                '9603-0702',
                '9603-0801',
                '9603-0802',
                '9603-0201',
                '9603-0202',
                '9603-0203',
                '9603-0204',
                '9603-0205',
                '9603-0206',
                '9603-0207',
                '9603-0208',
                '9603-0209',
                '9603-0210',
                '9603-0211',
                '9603-0212',
                '9603-0213',
                '9603-0214',
                '9603-0215',
                '9603-0216',
                '9603-0217',
                '9603-0218',
                '9603-0219',
                '9603-0220',
                '9603-0221',
                '9603-0222',
                '9603-0223',
                '9603-0224',
                '9603-0225',
                '9603-0226',
                '9603-0227',
                '9603-0228',
                '9603-0229',
                '9603-0230',
                '9603-0231',
                '9603-0232',
                '9603-0233',
                '9603-0234',
                '9603-0235',
                '9603-0236',
            ],
            'page': str(page),
            'startTime': '',
            'keyword': '',
            'isSortByCompanyCd': '1',
            'needFields[]': [
                'companyCd',
                'companyName',
                'disclosureTitle',
                'disclosurePostTitle',
                'destFilePath',
                'publishDate',
                'fileExt',
            ],
            'sortfield': 'publish_date',
            'sorttype': 'desc',
        }
        return data

    def start_requests(self):
        for page in range(self.start_page - 1, self.end_page + 1):
            data = self.generate_params(page)

            yield scrapy.FormRequest(
                url=self.base_url,
                method='POST',
                headers=self.headers,
                formdata=data,
                callback=self.parse_list,
                dont_filter=True,
            )

    def parse_list(self, response):
        result = response.text
        res = re.findall(r'null\(\[(.*?)]\)$', result)
        if res:
            res = json.loads(res[0])
            datas = res['listInfo']['content']
            for row in datas:
                bond_code = row['companyCd']
                params = {
                    'zqdm': bond_code,
                }
                separator = '&' if '?' in self.detail_url else '?'
                request_url = f'{self.detail_url}{separator}{urlencode(params)}'
                yield scrapy.Request(
                    url=request_url,
                    method='GET',
                    headers=self.headers,
                    callback=self.parse_detail,
                    dont_filter=True,
                )

    def parse_detail(self, response):
        result = response.text
        res = re.findall(r'null\((.*?)\)$', result)
        if res and res[0] != 'null':
            res = json.loads(res[0])
            bond_code = res['xxzqdm']
            bond_short_name = res['xxzqjc']
            bond_expand_short_name = res['xxzqjcex']
            bond_full_name = res['xxzqmc']
            issue_owner = res['xxfxr']
            issue_date = res['xxfxqsr']
            issue_end_date = res['xxfxjsr']

            interest_calculate_mode = res['xxllxs']
            interest_pay_cycle = res['xxfxzq'] + res['xxjxdw']

            issue_face_value = res['xxfxme']
            issue_num = res['xxfxl']
            issue_volume = (int(issue_num) * int(issue_face_value)) / 100000000

            trading_mode = res['xxjyfs']
            issue_term = res['xxzqqx']
            listing_date = res['xxssrq']
            due_date = res['xxdqr']

            bond_rating = res['xxzqpj']
            entity_rating = res['xxztpj']
            rating_outlook = res['xxzxztpjzw']
            issue_face_rate = res['xxpmll']
            md5_value = hash_md5(bond_code)

            items = {}
            items['bond_code'] = bond_code
            items['bond_short_name'] = bond_short_name
            items['bond_expand_short_name'] = bond_expand_short_name
            items['bond_full_name'] = bond_full_name
            items['bond_type'] = '公司债券'
            items['issue_owner'] = issue_owner
            items['issue_date'] = issue_date
            items['issue_end_date'] = issue_end_date
            items['interest_calculate_mode'] = interest_calculate_mode
            items['interest_pay_cycle'] = interest_pay_cycle
            items['bond_issue_volume'] = issue_volume
            items['listing_date'] = listing_date
            items['due_date'] = due_date
            items['issue_term'] = issue_term
            items['issue_face_value'] = issue_face_value
            items['trading_mode'] = trading_mode
            items['bond_rating'] = bond_rating
            items['entity_rating'] = entity_rating
            items['rating_outlook'] = rating_outlook
            items['issue_face_rate'] = issue_face_rate
            items['md5_value'] = md5_value
            # insert_data('entity_bond_finance', item)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
