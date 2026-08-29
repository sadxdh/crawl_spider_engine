import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *


# 全国法院-所有法院列表
class NationalCourtsAllListSpider(BaseSpider):
    name = 'national_courts_all_list'
    data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        },
        #'COOKIES_ENABLED': True  # 使用cookie字段必须得要
    }
    proxy_type = 'long_proxy'

    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Referer": "https://rmft.court.gov.cn/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": "\"Not;A=Brand\";v=\"8\", \"Chromium\";v=\"150\", \"Google Chrome\";v=\"150\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    def start_requests(self):
        url = "https://rmft.court.gov.cn/getOrganTree.jspx"
        params = {
            "siteId": "10"
        }
        yield scrapy.Request(
            url=f"{url}?{urlencode(params)}",
            headers=self.headers,
            callback=self.get_level_list,
            errback=self.errback,
        )

    def get_level_list(self, response):
        json_data = json.loads(response.text)
        for data in json_data['list'][0]['children']:
            level_court = data['name']
            md5_value = hash_md5(level_court)
            main_item = {}
            main_item['level_court'] = level_court
            main_item['md5_value'] = md5_value
            main_item['_table'] = 'court_info'
            yield main_item

            if data.get('haveChildren') is True:
                fy_id = data['id']
                url = "https://rmft.court.gov.cn/getOrganTree.jspx"
                params = {
                    "fyId": fy_id,
                    "siteId": "10"
                }
                yield scrapy.Request(
                    url=f"{url}?{urlencode(params)}",
                    headers=self.headers,
                    callback=self.get_secondary_list,
                    errback=self.errback,
                    cb_kwargs={'level_court': level_court}
                )

    def get_secondary_list(self, response, level_court):
        json_data = json.loads(response.text)
        for data in json_data['children']:
            secondary_court = data['name']
            md5_value = hash_md5(f"{level_court}{secondary_court}")
            main_item = {}
            main_item['level_court'] = level_court
            main_item['secondary_court'] = secondary_court
            main_item['md5_value'] = md5_value
            main_item['_table'] = 'court_info'
            yield main_item

            if data.get('haveChildren') is True:
                fy_id = data['id']
                url = "https://rmft.court.gov.cn/getOrganTree.jspx"
                params = {
                    "fyId": fy_id,
                    "siteId": "10"
                }
                yield scrapy.Request(
                    url=f"{url}?{urlencode(params)}",
                    headers=self.headers,
                    callback=self.get_third_list,
                    errback=self.errback,
                    cb_kwargs={'level_court': level_court, 'secondary_court': secondary_court}
                )

    def get_third_list(self, response, level_court, secondary_court):
        json_data = json.loads(response.text)
        for data in json_data['children']:
            third_court = data['name']
            md5_value = hash_md5(f"{level_court}{secondary_court}{third_court}")
            main_item = {}
            main_item['level_court'] = level_court
            main_item['secondary_court'] = secondary_court
            main_item['third_court'] = third_court
            main_item['md5_value'] = md5_value
            main_item['_table'] = 'court_info'
            yield main_item

            if data.get('haveChildren') is True:
                fy_id = data['id']
                url = "https://rmft.court.gov.cn/getOrganTree.jspx"
                params = {
                    "fyId": fy_id,
                    "siteId": "10"
                }
                yield scrapy.Request(
                    url=f"{url}?{urlencode(params)}",
                    headers=self.headers,
                    callback=self.get_fourth_list,
                    errback=self.errback,
                    cb_kwargs={'level_court': level_court, 'secondary_court': secondary_court, 'third_court': third_court}
                )

    def get_fourth_list(self, response, level_court, secondary_court, third_court):
        json_data = json.loads(response.text)
        for data in json_data['children']:
            fourth_court = data['name']
            md5_value = hash_md5(f"{level_court}{secondary_court}{third_court}{fourth_court}")
            main_item = {}
            main_item['level_court'] = level_court
            main_item['secondary_court'] = secondary_court
            main_item['third_court'] = third_court
            main_item['fourth_court'] = fourth_court
            main_item['md5_value'] = md5_value
            main_item['_table'] = 'court_info'
            yield main_item

            if data.get('haveChildren') is True:
                fy_id = data['id']
                url = "https://rmft.court.gov.cn/getOrganTree.jspx"
                params = {
                    "fyId": fy_id,
                    "siteId": "10"
                }
                yield scrapy.Request(
                    url=f"{url}?{urlencode(params)}",
                    headers=self.headers,
                    callback=self.get_fifth_list,
                    errback=self.errback,
                    cb_kwargs={'level_court': level_court}
                )

    def get_fifth_list(self, response, level_court, secondary_court, third_court, fourth_court):
        json_data = json.loads(response.text)
        for data in json_data['children']:
            fifth_court = data['name']
            md5_value = hash_md5(f"{level_court}{secondary_court}{third_court}{fourth_court}{fifth_court}")
            main_item = {}
            main_item['level_court'] = level_court  # 一级法院
            main_item['secondary_court'] = secondary_court  # 二级法院
            main_item['third_court'] = third_court  # 三级法院
            main_item['fourth_court'] = fourth_court  # 四级法院
            main_item['fifth_court'] = fifth_court  # 五级法院
            main_item['md5_value'] = md5_value
            main_item['_table'] = 'court_info'
            yield main_item




    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')