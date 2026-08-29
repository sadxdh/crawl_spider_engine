"""北京交易所"""
import hashlib, scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class BseHistorySpider(BaseSpider):
    name = 'company_report_bse_history_spider'
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
        'Accept': 'text/javascript, application/javascript, application/ecmascript, '
                  'application/x-ecmascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://www.bse.cn',
        'Referer': 'https://www.bse.cn/disclosure/announcement.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0',
        'X-Requested-With': 'XMLHttpRequest',
    }
    base_url = 'https://www.bse.cn/nqxxController/nqxxCnzq.do'
    detail_url = 'https://www.bse.cn/disclosureInfoController/productInfoResult.do'
    page = 0

    def start_requests(self):
        data = {
            'page': str(self.page),
            'typejb': 'T',
            'xxfcbj[]': '2',
            'xxzqdm': '',
            'sortfield': 'xxzqdm',
            'sorttype': 'asc',
        }
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
            datas = res['content']

            if len(datas) >= 20:
                self.page += 1
                yield from self.start_requests()
            for data in datas:
                security_code = data['xxzqdm']
                security_short = data['xxzqjc']
                get_detail_data = {'security_code': security_code, 'security_short': security_short}
                yield from self.get_detail(get_detail_data, 0)

    @staticmethod
    def generate_params(security_code, page):
        data = {
            'xxggfl[]': 'qb',
            'startTime': '',
            'companyCd': security_code,
            'keyword': '',
            'disclosureType[]': [
                '9530',
                '9537',
                '9538',
                '9506',
                '9503',
                '9504',
                '9505',
                '9510',
                '9520',
                '9605',
                '9533',
            ],
            'disclosureSubType[]': [
                '9601-1201',
                '9601-1404',
                '9601-1604',
                '9601-1501',
                '9601-1301',
                '9532-1001',
                '9601-1021',
                '9601-1022',
                '9601-1023',
                '9601-1208',
                '9601-1209',
                '9601-1024',
                '9601-1025',
                '9601-1026',
                '9601-1312',
                '9601-1313',
                '9601-1401',
                '9601-1402',
                '9601-1403',
                '9601-1413',
                '9601-1414',
                '9601-1601',
                '9601-1602',
                '9601-1603',
                '9601-1615',
                '9601-1616',
                '9601-1027',
                '9601-1028',
                '9601-1029',
                '9601-1508',
                '9601-1509',
                '9601-1202',
                '9601-1203',
                '9601-1204',
                '9601-1205',
                '9601-1206',
                '9601-1207',
                '9601-1106',
                '9601-1107',
                '9601-1405',
                '9601-1406',
                '9601-1407',
                '9601-1408',
                '9601-1409',
                '9601-1410',
                '9601-1411',
                '9601-1412',
                '9601-1502',
                '9601-1503',
                '9601-1504',
                '9601-1505',
                '9601-1506',
                '9601-1507',
                '9601-1014',
                '9601-1015',
                '9601-1605',
                '9601-1606',
                '9601-1607',
                '9601-1608',
                '9601-1609',
                '9601-1610',
                '9601-1611',
                '9601-1612',
                '9601-1302',
                '9601-1303',
                '9601-1304',
                '9601-1305',
                '9601-1306',
                '9601-1307',
                '9601-1012',
                '9601-1013',
                '9601-1701',
                '9601-1702',
                '9601-1703',
                '9601-1704',
                '9601-1705',
                '9601-1706',
                '9601-1707',
                '9601-1708',
                '9601-1709',
                '9601-1710',
                '9601-1711',
                '9601-1712',
                '9601-1715',
                '9601-1716',
            ],
            'wxhType': 'wxh',
            'zljgcsType': 'zljgcs',
            'jlcfType': 'jlcf',
            'newThreeArray[]': '3',
            'siteId': '6',
            'sortfield': 'publishDate',
            'sorttype': 'desc',
            'page': str(page),
        }
        return data

    def get_detail(self, data, detail_page):
        security_code = data['security_code']
        security_short = data['security_short']
        params = self.generate_params(security_code, detail_page)
        yield scrapy.FormRequest(
            url=self.detail_url,
            method='POST',
            headers=self.headers,
            formdata=params,
            callback=self.parse_detail,
            cb_kwargs={'security_short': security_short, 'detail_page': detail_page, 'get_detail_data': data},
            dont_filter=True,
        )

    def parse_detail(self, response, security_short, detail_page, get_detail_data):
        result = response.text
        res = re.findall(r'null\(\[(.*?)]\)$', result)
        if res:
            res = json.loads(res[0])
            datas = res['listInfo']['content']

            for data in datas:
                publish_time = data['publishDate']
                announcement_title = data['disclosureTitle']
                announcement_url = urljoin('https://www.bse.cn/', data['destFilePath'])
                cate_name = self.get_cate_name(data['disclosureType'])
                security_code = data['companyCd']

                source = '北交所'
                md5_value = hash_md5(str(publish_time) + announcement_title + security_code)

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

            if len(datas) >= 20:
                detail_page += 1
                if detail_page <= 100:
                    yield from self.get_detail(get_detail_data, detail_page)

    @staticmethod
    def get_cate_name(cate_code):
        cate_type = {
            '发行上市审核': ['9530', '9537', '9538'],
            '公司公告': ['9503', '9504', '9505', '9510', '9520', '9605', '9533'],
            '北交所公告': ['9506'],
            '问询函': ['wxh'],
            '纪律处分': ['jlcf'],

        }
        for cate_name, cate_code_list in cate_type.items():
            if cate_code in cate_code_list:
                return cate_name
        return None

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')