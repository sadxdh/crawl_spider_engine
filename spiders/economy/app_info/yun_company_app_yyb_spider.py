import json
from scrapy import FormRequest, Request

from spiders.base_spider import BaseSpider
from utils.time_kit import *
from utils.tools import *


class YunYingYongBaoSpider(BaseSpider):
    name = 'yun_company_app_yyb'
    data_table = 'app_info'
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'
    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'cache-control': 'no-cache',
        'content-type': 'text/plain;charset=UTF-8',
        'origin': 'https://sj.qq.com',
        'referer': 'https://sj.qq.com/',
    }

    def generate_data(self, page):
        data = {
            "head": {
                "cmd": "dc_pcyyb_official",
                "authInfo": {"businessId": "AuthName"},
                "deviceInfo": {"platformType": 1},
                "userInfo": {"guid": "6d6b18a0-6cee-4c99-9742-bbf3d7172895"},
                "expSceneIds": "",
                "hostAppInfo": {"scene": "app_center"}
            },
            "body": {
                "bid": "yybhome",
                "offset": 0,
                "size": 10,
                "preview": False,
                "listS": {
                    "region": {"repStr": ["CN"]},
                    "cate_alias": {"repStr": ["all"]}
                },
                "listI": {
                    "limit": {"repInt": [24]},
                    "offset": {"repInt": ["%s"%page]}
                },
                "layout": "YYB_HOME_APP_LIBRARY_LIST"
            }
        }
        return data

    def generate_game_data(self, page):
        data = {
            'head': {
                'cmd': 'dc_pcyyb_official',
                'authInfo': {'businessId': 'AuthName'},
                'deviceInfo': {'platformType': 1},
                'userInfo': {'guid': 'ecb14753-d010-495b-8f98-7ee56549bf7e'},
                'expSceneIds': '92170',
                'hostAppInfo': {'scene': 'game_center'}
            },
            'body': {
                'bid': 'yybhome',
                'offset': 0,
                'size': 10,
                'preview': False,
                'listS': {
                    'region': {'repStr': ['CN']},
                    'tag_alias': {'repStr': ['all']}
                },
                'listI': {
                    'limit': {'repInt': [24]},
                    'offset': {'repInt': ["%s"%page]}
                },
                'layout': 'YYB_HOME_GAME_LIBRARY_LIST_ALGRITHM'
            }
        }
        return data

    def start_requests(self):
        pages = [i for i in range(int(self.start_page), int(self.end_page) + 1)]
        for page in pages:
            soft_data = self.generate_data(page)
            game_data = self.generate_game_data(page)

            for app_type, data in {'软件': soft_data, '游戏': game_data}.items():
                yield FormRequest(
                    url='https://yybadaccess.3g.qq.com/v2/dc_pcyyb_official',
                    method='post',
                    headers=self.headers,
                    body=json.dumps(data),
                    meta={'app_type': app_type},
                    callback=self.parse,
                    dont_filter=True
                )

    def parse(self, response, **kwargs):
        app_type = response.meta.get('app_type')
        result = response.json()
        datas = result['data']['components'][0]['data']['itemData']
        for data in datas:
            app_name = data['name']  # app名称
            app_icon = data['icon']  # app图标
            developer = data['developer']  # 开发者
            operator = data['operator']  # 运营商
            tags = data['tags']  # 标签
            ios_url = data.get('ios_url')  # ios版链接
            abstract = data.get('editor_intro')  # app介绍
            version = data.get('version_name')  # 版本
            update_time = data.get('update_time')  # 更新时间
            average_rating = data.get('average_rating')  # 评分
            apk_size = data.get('apk_size')  # 安装包大小
            list_data = {
                'app_name': app_name,
                'app_icon': app_icon,
                'developer': developer,
                'operator': operator,
                'tags': tags,
                'ios_url': ios_url,
                'abstract': abstract,
                'version': version,
                'update_time': update_time,
                'average_rating': average_rating,
                'apk_size': apk_size+' b',
                'app_type': app_type,
            }

            pkg_name = data.get('pkg_name')  # 详情链接
            detail_url = f'https://sj.qq.com/appdetail/{pkg_name}'

            yield Request(
                url=detail_url,
                headers=self.headers,
                body=json.dumps(data),
                meta={'list_data': list_data},
                callback=self.parse_detail,
                dont_filter=True
            )

    def parse_detail(self, response):
        meta = response.meta
        list_data = meta.get('list_data')

        images = response.xpath('//div[@class="GameDetail_previewContainer__QyEUQ"]/div/div/ul/li/div/picture/img/@src').getall()
        images = json.dumps(images)
        summary = response.xpath('//div[@class="GameDetail_descriptionContainer__x6_ff"]/p/text()').get()

        app_name = list_data.get('app_name')
        developer = list_data['developer']
        update_time = str(timestamp_to_datetime(list_data['update_time']))

        item = {}
        item['md5_value'] = hash_md5(app_name + developer + 'android')
        item['app_name'] = list_data['app_name']
        item['app_icon'] = list_data['app_icon']
        item['developer'] = developer
        item['operator'] = list_data['operator']
        item['ios_url'] = list_data['ios_url']
        item['version'] = list_data['version']
        item['update_date'] = update_time
        item['average_rating'] = list_data['average_rating']
        item['apk_size'] = list_data['apk_size']
        item['abstract'] = list_data['abstract']
        item['summary'] = summary
        item['tags'] = list_data['tags']
        item['images'] = images
        item['type'] = list_data['app_type']
        item['platform'] = 'android'
        yield item
