import hashlib, scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *


class SZseBondAnnouncementSpider(BaseSpider):
    name = 'szse_report_bond_announcement'
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
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Content-Type': 'application/json',
        'Origin': 'https://www.szse.cn',
        'Referer': 'https://www.szse.cn/disclosure/bond/notice/index.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0',
        'X-Request-Type': 'ajax',
        'X-Requested-With': 'XMLHttpRequest',
    }
    base_url = 'https://www.szse.cn/api/disc/announcement/annList'
    bond_announce_type = {
        "013901": "债券发行上市",
        "013903": "债券定期公告",
        "013904": "债券付息公告",
        "013905": "债券到期兑付、停止交易公告",
        "013999": "债券其它公告",
        "0109": "可转换债券"
    }

    @staticmethod
    def generate_params(category_id, page):
        json_data = {
            'seDate': [
                '',
                '',
            ],
            'channelCode': ['bondinfoNotice_disc'],
            'smallCategoryId': [category_id],
            'pageSize': 50,
            'pageNum': page,
        }
        return json_data

    def start_requests(self):
        for category_id, category_name in self.bond_announce_type.items():
            for page in range(int(self.start_page), int(self.end_page) + 1):
                json_data = self.generate_params(category_id, page)
                yield scrapy.Request(
                    url=self.base_url,
                    method='POST',
                    headers=self.headers,
                    body=json.dumps(json_data, separators=(',', ':'), ensure_ascii=False),
                    callback=self.parse_list,
                    cb_kwargs={'category_name': category_name},
                    dont_filter=True,
                )

    def parse_list(self, response, category_name):
        result = response.json()
        datas = result['data']
        for data in datas:
            bond_code = data['secCode'][0]
            bond_short_name = data['secName'][0]
            announcement_title = data['title']
            announcement_date = data['publishTime']
            href = data['attachPath']
            announcement_url = urljoin('https://disc.static.szse.cn/download/', href)
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
            items['source'] = '深交所'
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