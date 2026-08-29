import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.economy.app_info.dd_data import DdDataSpider
from spiders.economy.app_info.login import DdLogin
from utils.tools import *
from utils.time_kit import *
from utils.db.redis_opt import *

class AppInfoIosListSpider(BaseSpider):
    name = 'app_info_ios_list'
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

    rank_type = {'应用': 1, '游戏': 2, '总榜': 4}
    brand_id = {'免费榜': 2, '付费榜': 3, '畅销榜': 4}
    app_genre_id = {
        '全部应用': 173,
        '摄影与录像': 132,
        '娱乐': 134,
        '教育': 135,
        '效率': 176,
        '社交': 137,
        '生活': 138,
        '购物': 149,
        '工具': 140,
        '音乐': 141,
        '图书': 142,
        '商务': 143,
        '财务': 144,
        '美食佳饮': 145,
        '健康健美': 146,
        '报刊杂志': 147,
        '医疗': 148,
        '导航': 149,
        '新闻': 150,
        '参考资料': 151,
        '体育': 152,
        '旅游': 153,
        '天气': 154,
        '软件开发工具': 155,
        '儿童': 174,
        '图形与设计': 157,

    }
    game_genre_id = {
        '全部游戏': 172,
        '益智解谜': 157,
        '动作': 158,
        '角色扮演': 159,
        '策略': 160,
        '休闲': 161,
        '体育': 162,
        '模拟': 163,
        '冒险': 164,
        '家庭聚会': 165,
        '桌面': 166,
        '卡牌': 167,
        '音乐': 168,
        '竞速': 169,
        '问答': 170,
        '字谜': 171,
        '娱乐场': 175
    }

    def get_cookies(self):
        cookies_dict = hgetall(self.ddDataSpider.COOKIE_REDIS_KEY)
        if not cookies_dict or not self.cookie_status:
            cookies = DdLogin().generate_cookie()
            return cookies
        else:
            email, cookies = random.choice(list(cookies_dict.items()))
            return json.loads(cookies)

    def generate_aes_params(self, rank_type):
        # 初始化aes加密参数
        self.aes_params = self.ddDataSpider.get_aes_param(
            # url=f'https://app.diandian.com/rank/ios/1-{rank_type}-0-75-2',
            # headers=self.aes_headers,
            # params={'time': '', 'device': '1', 'timetype': ''},
            url=f'https://static.diandian.com/_app/app~dd2ce1b5.d39ea9a.js',
            headers=self.aes_headers,
            proxies_type=True
        )
        if self.aes_params == {}:
            self.aes_params = {'s': '1c475deae1df66347b0a757d8861e31f', 'k': '9836828ceb09268d', 'l': '8bca24d7845d4a97', 'd': ''}

    def generate_params(self, page, rank_type, brand_id, genre_id):
        params = {
            'market_id': '1',
            'genre_id': str(genre_id),
            'country_id': '75',
            'device_id': '1',
            'page': str(page),
            'time': return_timestamp(digit=10),
            'rank_type': str(rank_type),
            'brand_id': str(brand_id),
        }
        aes_param = self.aes_params | {"d": -1, "sort": "dd", "num": 10}

        k = self.ddDataSpider.generate_k(
            e=params,
            path='/v1/rank',
            n=aes_param,
            r='get'
        )
        params = params | {'k': k}
        return params

    def start_requests(self):
        for rank_name, rank_type in self.rank_type.items():
            self.generate_aes_params(rank_type)
            for brand_name, brand_id in self.brand_id.items():
                if rank_name == '应用':
                    genre_info = self.app_genre_id
                elif rank_name == '游戏':
                    genre_info = self.game_genre_id
                else:
                    genre_info = {}
                for genre_name, genre_id in genre_info.items():
                    for page in range(self.start_page, self.end_page + 1):
                        yield from self.get_list(page, rank_name, rank_type, brand_name, brand_id, genre_name, genre_id)

    def get_list(self, page, rank_name, rank_type, brand_name, brand_id, genre_name, genre_id):
        logger.info(f'{self.name} 列表执行 rank:{rank_name} brand:{brand_name} genre:{genre_name} page:{page}')
        params = self.generate_params(page, rank_type, brand_id, genre_id)
        cookies = self.get_cookies()
        self.cookie_status = True
        response = common_request(
            url='https://api.diandian.com/pc/app/v1/rank',
            headers=self.headers,
            params=params,
            cookies=cookies,
            proxies_type=True
        )
        if response:
            yield from self.parse_list(response, rank_name, brand_name, genre_name)

    def parse_list(self, response, rank_name, brand_name, genre_name):
        result = response.json()
        if result.get('code') == 9 or result.get('msg') == "尚未登录" or result.get('msg') == '当前账号同时登录的设备数超限':
            logger.warning(f'{self.name} 请求异常, cookie_status设置为 False')
            self.cookie_status = False
        else:
            data = result.get('data')
            if data and isinstance(data, dict):
                apps = data['apps']
                ranks = data['ranks']

                for app in apps:
                    app_id = app['app_id']
                    en_app_id = app['id']
                    app_name = app['name']  # app名称
                    logo = app['logo']
                    release_time = app['last_release_time']
                    developer = app['developer']['name']
                    price = app['price']  # 价格
                    unit = app['price_unit']  # 单位
                    rating = app['rating']  # 评分
                    rating_count = app['rating_count']  # 评分数
                    genres = json.dumps(app['genres'])  # 分类信息
                    release_date = str(timestamp_to_datetime(release_time).date())

                    md5_value = hash_md5(rank_name + brand_name + genre_name + app_name + release_date)

                    # item = APPListItem()
                    items = {}
                    items['rank_name'] = rank_name
                    items['brand_name'] = brand_name
                    items['sub_brand_name'] = genre_name
                    items['app_id'] = app_id
                    items['en_app_id'] = en_app_id
                    items['app_name'] = app_name
                    items['logo'] = logo
                    items['release_date'] = release_date
                    items['developer'] = developer
                    items['price'] = price
                    items['unit'] = unit
                    items['rating'] = rating
                    items['rating_count'] = rating_count
                    items['genres'] = genres
                    items['platform'] = 'ios'
                    items['md5_value'] = md5_value
                    # insert_data('app_list', item)
                    items['_table'] = 'app_list'
                    yield items


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')