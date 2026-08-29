import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.economy.app_info.dd_data import DdDataSpider
from spiders.economy.app_info.login import DdLogin
from utils.mysql_tools import select_data
from utils.tools import *
from utils.time_kit import *
from utils.db.redis_opt import *

class AppInfoIosDeteilInfoSpider(BaseSpider):
    # ios app 详情信息
    name = 'app_info_ios_deteil_info'
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
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Origin': 'https://app.diandian.com',
        'Pragma': 'no-cache',
        'Referer': 'https://app.diandian.com/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
        'language': 'zh',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Microsoft Edge";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    aes_headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;'
                  'q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'referer': 'https://app.diandian.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
    }
    aes_params = {}
    cookie_status = True
    ddDataSpider = DdDataSpider()

    @staticmethod
    def query_app_id(start_page, end_page):
        num = int(end_page) - int(start_page)
        condition = f'platform="ios" ORDER BY id DESC LIMIT {num} OFFSET {start_page}'
        data = ['app_id', 'en_app_id', 'app_name', 'genres', 'rank_name']
        datas = select_data(table='app_list', data=data, condition=condition)
        return datas

    def generate_aes_params(self, data):
        # 初始化aes加密参数
        app_id = data['app_id']
        app_name = data['app_name']
        en_app_id = data['en_app_id']
        self.aes_params = self.ddDataSpider.get_aes_param(
            # url=f'https://app.diandian.com/app/{en_app_id}/ios',
            # headers=self.aes_headers,
            # params={
            #     'market': '1',
            #     'country': '75',
            #     'id': app_id,
            #     'n': app_name,
            # }
            url=f'https://static.diandian.com/_app/app~dd2ce1b5.d39ea9a.js',
            headers=self.aes_headers,
            proxies_type=True
        )
        if self.aes_params == {}:
            self.aes_params = {'s': '1c475deae1df66347b0a757d8861e31f', 'k': '9836828ceb09268d', 'l': '8bca24d7845d4a97', 'd': ''}

    def generate_detail_params(self, data):
        params = {
            'id': data['en_app_id'],
            'country_id': '75',
            'language_id': '3',
        }

        aes_param = self.aes_params | {"d": 0, "sort": "dd", "num": 10}
        k = self.ddDataSpider.generate_k(params, path='/v1/app/more', n=aes_param, r='get')
        params = params | {'k': k}
        return params

    def get_cookies(self):
        cookies_dict = hgetall(self.ddDataSpider.COOKIE_REDIS_KEY)
        if not cookies_dict or not self.cookie_status:
            cookies = DdLogin().generate_cookie()
            return cookies
        else:
            email, cookies = random.choice(list(cookies_dict.items()))
            return json.loads(cookies)

    def start_requests(self):
        datas = self.query_app_id(self.start_page, self.end_page)
        for data in datas:
            self.generate_aes_params(data)
            yield from self.get_detail(data)

    def get_detail(self, data):
        params = self.generate_detail_params(data)
        cookies = self.get_cookies()
        response = common_request(
            url='https://api.diandian.com/pc/app/v1/app/more',
            headers=self.headers,
            params=params,
            cookies=cookies
        )
        if response:
            yield from self.parse_detail(response, data)

    def parse_detail(self, response, data):
        rank_name = data['rank_name']
        genres = json.loads(data['genres'])

        result = response.json()['data']

        # app相关
        app_name = result['name']
        app_icon = result['logo']
        genre_id = result['genre_id']

        tags = None
        for genre in genres:
            if genre_id == genre['id']:
                tags = genre['name']

        app_type = '软件' if rank_name == '应用' else rank_name
        rating = result['all_rating']
        abstract = result['title']
        version = result['version']  # 版本
        release_date = timestamp_to_datetime(result['last_release_time'])  # 最新更新时间
        description = result['description']  # app描述
        size = result['sizes']
        size = f'{int(size)/1024/1024}MB'

        # 开发者相关
        developer_info = result['developer']
        developer = developer_info['name']  # 开发者

        # ios应用截图
        pictures = result['screenshots'][0]['list']
        images = json.dumps(pictures)

        md5_value = hash_md5(app_name + developer + 'ios')
        # item = APPDetailsItem()
        items = {}
        items['md5_value'] = md5_value
        items['app_name'] = app_name
        items['app_icon'] = app_icon
        items['tags'] = tags
        items['type'] = app_type
        items['developer'] = developer
        items['abstract'] = abstract
        items['average_rating'] = rating
        items['version'] = version
        items['update_date'] = release_date
        items['summary'] = description
        items['images'] = images
        items['apk_size'] = size
        items['platform'] = 'ios'
        # insert_data('app_info', item)
        items['_table'] = 'app_info'
        yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')