import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *


class LawRegulationsNpcSpider(BaseSpider):
    name = 'law_regulations_npc'
    data_table = 'law_regulation'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        },
        # 'COOKIES_ENABLED': True  # 使用cookie字段必须得要
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://flk.npc.gov.cn',
        'Referer': 'https://flk.npc.gov.cn/search',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0',
    }

    status = {
        3: '有效',
        4: '尚未生效',
        2: '已修改',
        1: '已废止',
    }
    law_types = {
        '宪法': [100],
        '法律': [101, 102, 110, 120, 130, 140, 150, 155, 160, 170, 180, 190, 195, 200],
        '行政法规': [201, 210, 215],
        '监察法规': [220],
        '司法解释': [311, 320, 330, 340, 350],
        '地方性法规': [221, 222, 230, 260, 270, 290, 295, 300, 305, 310],
    }

    @staticmethod
    def generate_params(code_id, page):
        params = {
            'searchRange': 1,
            'sxrq': [],
            'gbrq': [],
            'searchType': 2,
            'sxx': [],
            'gbrqYear': [],
            'flfgCodeId': code_id,
            'zdjgCodeId': [],
            'searchContent': '',
            'orderByParam': {
                'order': '-1',
                'sort': '',
            },
            'pageNum': page,
            'pageSize': 20,
        }
        return params

    def start_requests(self):
        yield scrapy.Request(
            url = 'https://flk.npc.gov.cn/law-search/search/enumData',
            method = 'GET',
            headers=self.headers,
            callback=self.get_list,
        )

    def get_list(self, response):
        json_data = response.json()
        for law_category_code_id in json_data['data']['flfgfl']['children']:
            law_category = law_category_code_id['name'].replace('地方法规', '地方性法规')
            code_id = law_category_code_id['codeIdList']
            for page in range(self.start_page, self.end_page + 1):
                params = self.generate_params(code_id, page)
                yield scrapy.Request(
                    url="https://flk.npc.gov.cn/law-search/search/list",
                    method="POST",
                    headers=self.headers,
                    body=json.dumps(params, ensure_ascii=False).encode("utf-8"),
                    callback=self.parse_list,
                    dont_filter=True,
                    cb_kwargs={'law_category': law_category}
                )

    def parse_list(self, response, law_category):
        rows = response.json()['rows']
        for row in rows:
            detail_id = row['bbbs']
            title = row['title']
            formulating_authority = row['zdjgName']
            law_nature = row['flxz']
            timeliness = self.status.get(row['sxx'], 'xxx')
            publish_date = row['gbrq']
            entry_into_force_time = row['sxrq']
            temp = {
                'detail_id': detail_id,
                'title': title,
                'formulating_authority': formulating_authority,
                'law_nature': law_nature,
                'timeliness': timeliness,
                'publish_date': publish_date,
                'entry_into_force_time': entry_into_force_time,
            }
            yield from self.get_detail(temp, law_category)

    def get_detail(self, data, law_category):
        detail_id = data['detail_id']
        announcement_url = f'https://flk.npc.gov.cn/law-search/download/mobile?format=docx&bbbs={detail_id}'

        title = data['title']
        timeliness = data['timeliness']
        md5_value = hash_md5(title + timeliness)
        items = {}
        # item = LawRegulationItem()
        # item.spider_name = self.spider_name
        items['md5_value'] = md5_value
        items['title'] = data['title']
        items['formulating_authority'] = data['formulating_authority']
        items['law_nature'] = data['law_nature']
        items['timeliness'] = data['timeliness']
        items['publish_date'] = data['publish_date']
        items['entry_into_force_time'] = data['entry_into_force_time']
        items['law_category'] = law_category
        items['announcement_title'] = title
        items['announcement_url'] = announcement_url
        # insert_data('law_regulation', data=item)
        yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
