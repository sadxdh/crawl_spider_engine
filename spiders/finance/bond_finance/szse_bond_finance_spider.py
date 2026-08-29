import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class BondFinanceSzseSpider(BaseSpider):
    name = 'bond_finance_szse'
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
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Content-Type': 'application/json',
        'Referer': 'https://www.szse.cn/market/product/bond/cb/index.html',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0',
        'X-Request-Type': 'ajax',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Microsoft Edge";v="128"',
        'sec-ch-ua-platform': '"Windows"',
    }

    base_url = 'https://www.szse.cn/api/report/ShowReport/data'
    bond_type_list = [
        {'bond_type': '国债', 'sql_id': 'cpml_zq_guoz', 'count': 11},
        {'bond_type': '地方政府债券', 'sql_id': 'cpml_zq_zhengfuz', 'count': 542},
        {'bond_type': '政策性金融债', 'sql_id': 'cpml_zq_jrz', 'count': 1},
        {'bond_type': '政府支持债券', 'sql_id': 'cpml_zq_zfzcz', 'count': 5},
        {'bond_type': '公司债券（含企业债券）', 'sql_id': 'cpml_zq_gsz', 'count': 62},
        {'bond_type': '非公开发行公司债券', 'sql_id': 'cpml_zq_ints', 'count': 39},
        {'bond_type': '非公开发行可交换公司债券', 'sql_id': 'cpml_zq_intskjh', 'count': 2},
        # {'bond_type': '可转换债券', 'sql_id': '1277', 'count': 15},
        {'bond_type': '证券公司次级债券', 'sql_id': 'cpml_zq_cjz', 'count': 1},
        {'bond_type': '证券公司短期债券', 'sql_id': 'cpml_zq_cpxx', 'count': 1},
        {'bond_type': '企业资产支持证券', 'sql_id': 'cpml_zq_zczq', 'count': 101},
        {'bond_type': '不动产投资信托', 'sql_id': 'cpml_zq_reits_cplb', 'count': 8},
        {'bond_type': '创新品种', 'sql_id': 'cpml_zq_cxpz', 'count': 102},
    ]

    @staticmethod
    def generate_params(catalog_id, page):
        params = {
            'SHOWTYPE': 'JSON',
            'CATALOGID': catalog_id,
            'TABKEY': 'tab1',
            'PAGENO': str(page),
        }
        return params

    def start_requests(self):
        for bond_type_info in self.bond_type_list:
            bond_type = bond_type_info['bond_type']
            catalog_id = bond_type_info['sql_id']
            count_page = bond_type_info['count']
            end_pages = count_page if self.end_page > 999 else self.end_page
            for page in range(self.start_page, int(end_pages) + 1):
                params = self.generate_params(catalog_id, page)
                separator = '&' if '?' in self.base_url else '?'
                request_url = f'{self.base_url}{separator}{urlencode(params)}'

                yield scrapy.Request(
                    url=request_url,
                    method='GET',
                    headers=self.headers,
                    callback=self.parse_list,
                    cb_kwargs={'bond_type': bond_type,},
                    dont_filter=True,
                )

    def parse_list(self, response, bond_type):
        result = response.json()
        datas = result[0]['data']
        for data in datas:
            bond_code_res = data.get('zqdm')
            bond_code_res = bond_code_res if bond_code_res else data.get('zqdh')
            bond_code = self.match_bond_code(bond_code_res)

            bond_short_name = data['zqjc']
            bond_short_name = bond_short_name.split('<a')[0] if '<a' in bond_short_name else bond_short_name

            listing_date = data.get('ssrq')
            effective_transfer_date = data.get('zrqsr')
            due_date = data.get('dqrq')
            due_date = due_date if due_date else data.get('dqr')

            issue_face_rate = data.get('pmll')

            issue_volume = data.get('fxlyy')
            issue_volume = issue_volume if issue_volume else data.get('fxlwz')
            issue_volume = issue_volume if issue_volume else data.get('fxl')

            is_guarantee = data['dbjs']
            trading_mode = data['jyfs']
            value_date = data.get('qxrq')
            yield_rate = data.get('yqsyl')
            yield_rate = yield_rate if yield_rate else None
            trustee = data.get('glrjc')

            md5_value = hash_md5(bond_code)

            items = {}
            items['bond_code'] = bond_code
            items['bond_short_name'] = bond_short_name
            items['bond_type'] = bond_type
            items['bond_issue_volume'] = issue_volume.replace(',', '')
            items['listing_date'] = listing_date
            items['due_date'] = due_date
            items['value_date'] = value_date
            items['issue_face_rate'] = issue_face_rate
            items['effective_transfer_date'] = effective_transfer_date
            items['trading_mode'] = trading_mode.replace('<br>', '')
            items['is_guarantee'] = is_guarantee
            items['yield_rate'] = yield_rate
            items['trustee'] = trustee
            items['md5_value'] = md5_value
            # insert_data('entity_bond_finance', item)
            yield items

    @staticmethod
    def match_bond_code(value):
        match_res = re.findall(r'<u>(.*?)</u>', value)
        res = match_res[0] if match_res else None
        return res

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')