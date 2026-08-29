import hashlib, scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *


class BseBondAnnouncementSpider(BaseSpider):
    name = 'bse_report_bond_announcement'
    data_table = 'entity_bond_announcement'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'text/javascript, application/javascript, application/ecmascript,'
                  ' application/x-ecmascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://www.bse.cn',
        'Referer': 'https://www.bse.cn/disclosure/xyznotice.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0',
        'X-Requested-With': 'XMLHttpRequest',
    }
    base_url = 'https://www.bse.cn/disclosureInfoController/zoneInfoResult.do'
    bond_announce_type = {
        '发行': [
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
        ],
        '上市': '9602-0301',
        '定期报告': [
            '9603-0101',
            '9603-0102',
            '9603-0103',
            '9603-0104',
        ],
        '可交债': [
            '9603-0301',
            '9603-0302',
        ],
        '停复牌': [
            '9603-0401',
            '9603-0402',
        ],
        '派息兑付及摘牌': [
            '9603-0601',
            '9603-0602',
            '9603-0603',
        ],
        '评级': [
            '9603-0701',
            '9603-0702',
        ],
        '受托': [
            '9603-0801',
            '9603-0802',
        ],
        '其他': [
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
    }

    @staticmethod
    def generate_params(category_id, page):
        data = {
            'companyCd': '',
            'disclosureSubtypes[]': category_id,
            'page': str(page),
            'startTime': '',
            'endTime': '',
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
        for category_name, category_id in self.bond_announce_type.items():
            for page in range(int(self.end_page) + 1):
                data = self.generate_params(category_id, page)
                yield scrapy.FormRequest(
                    url=self.base_url,
                    method='POST',
                    headers=self.headers,
                    formdata=data,
                    callback=self.parse_list,
                    cb_kwargs={'category_name': category_name},
                    dont_filter=True,
                )

    def parse_list(self, response, category_name):
        result = response.text
        res = re.findall(r'null\(\[(.*?)]\)$', result)
        if res:
            res = json.loads(res[0])
            datas = res['listInfo']['content']

            for data in datas:
                bond_code = data['companyCd']
                bond_short_name = data['companyName']
                announcement_title = data['disclosureTitle']
                announcement_date = data['publishDate']
                href = data['destFilePath']
                announcement_url = urljoin('https://www.bse.cn/', href)
                announcement_group = self.generate_announcement_group(announcement_title)
                md5_value = hash_md5(bond_code + announcement_title + announcement_date)

                items = {}
                items['bond_code'] = bond_code
                items['bond_short_name'] = bond_short_name
                items['announcement_title'] = announcement_title
                items['announcement_date'] = announcement_date
                items['announcement_url'] = announcement_url
                items['announcement_type'] = category_name
                items['announcement_group'] = announcement_group
                items['md5_value'] = md5_value
                items['source'] = '北交所'
                # insert_data('entity_bond_announcement', item)
                yield items

    @staticmethod
    def generate_announcement_group(announcement_title):
        if (('未能按期' in announcement_title or
             '未按期' in announcement_title or
             '未能清偿' in announcement_title) and
                '进展' not in announcement_title):
            announcement_group = '债券违约'
        elif '风险提示' in announcement_title:
            announcement_group = '违约提示'
        elif '债券和解' in announcement_title:
            announcement_group = '违约偿付'
        else:
            announcement_group = None
        return announcement_group

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')