import hashlib, scrapy
from urllib.parse import urlencode

from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *


class SseBondAnnouncementSpider(BaseSpider):
    name = 'sse_report_bond_announcement'
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
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://www.sse.com.cn/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0',
    }
    base_url = 'https://query.sse.com.cn/commonSoaQuery.do'
    bond_type = {
        'NATIONAL_BOND_BULLETIN': 54,
        'LOCAL_GOVERNMENT_BOND_BULLETIN': 685,
        'CORPORATE_BOND_BULLETIN,COMPANY_BOND_BULLETIN': 29230,
        'EXCHANGEABLE_COMPANY_BOND_BULLETIN': 96,
        'NON_PUBLIC_COMPANY_BOND_BULLETIN': 180,
        'CORPORATE_ASSET_BOND_BULLETIN': 772,
    }

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

    @staticmethod
    def generate_params(bond_type, page):
        params = {
            'isPagination': 'true',
            'pageHelp.pageSize': '25',
            'pageHelp.cacheSize': '1',
            'type': 'inParams',
            'sqlId': 'BS_ZQ_GGLL',
            'sseDate': '2000-01-01 00:00:00',
            'sseDateEnd': f'{str(return_tomorrow())} 23:59:59',
            'securityCode': '',
            'title': '',
            'orgBulletinType': '',
            'bondType': bond_type,
            'order': 'sseDate|desc,securityCode|asc,bulletinId|asc',
            'pageHelp.pageNo': page,
            'pageHelp.beginPage': page,
            'pageHelp.endPage': page,
        }
        return params

    def start_requests(self):
        for bond_type, pages in self.bond_type.items():
            end_pages = pages if int(self.end_page) < 0 else self.end_page
            for page in range(int(self.start_page), int(end_pages) + 1):
                params = self.generate_params(bond_type, page)
                request_url = f'{self.base_url}?{urlencode(params)}'
                yield scrapy.Request(
                    url=request_url,
                    method='GET',
                    headers=self.headers,
                    callback=self.parse_list,
                    dont_filter=True,
                )

    def parse_list(self, response):
        result = response.json()
        rows = result['result']
        for row in rows:
            bond_code = row['securityCode']
            bond_short_name = row['securityAbbr']
            bond_type = row['bulletinHeading']
            announcement_title = row['title']
            announcement_date = row['sseDate']
            announcement_url = urljoin(response.url, row['url'])
            announcement_type = row['bulletinType']
            announcement_group = self.generate_announcement_group(announcement_title)

            md5_value = hash_md5(bond_code + announcement_title + announcement_date)

            items = {}
            items['bond_code'] = bond_code
            items['bond_short_name'] = bond_short_name
            items['bond_type'] = bond_type
            items['announcement_title'] = announcement_title
            items['announcement_date'] = announcement_date
            items['announcement_url'] = announcement_url
            items['announcement_type'] = announcement_type
            items['announcement_group'] = announcement_group
            items['md5_value'] = md5_value
            items['source'] = '上交所'
            # insert_data('entity_bond_announcement', item)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')