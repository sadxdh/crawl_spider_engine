import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.economy.app_info.login import DdLogin
from utils.tools import *
from utils.time_kit import *
from spiders.economy.app_info.dd_data import DdDataSpider
from utils.db.redis_opt import *

class AppInfoAndroidListSpider(BaseSpider):
    # 安卓榜单-只要华为的
    name = 'app_info_android_list'
    data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            # 'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        },
        'COOKIES_ENABLED': True  # 使用cookie字段必须得要
    }
    # proxy_type = 'long_proxy'

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

    brand_id = {'应用': 201, '游戏': 202}

    app_sub_brand_id = {
        '全部应用': 0,
        '影音娱乐': 901977,
        '实用工具': 901991,
        '社交通讯': 901998,
        '教育': 902003,
        '新闻阅读': 902014,
        '拍摄美化': 902022,
        '美食': 902029,
        '出行导航': 902042,
        '旅游住宿': 902052,
        '购物比价': 902061,
        '商务': 902069,
        '儿童': 902079,
        '金融理财': 902084,
        '运动健康': 902090,
        '便捷生活': 902096,
        '汽车': 902103,
        '个性主题': 902108
    }
    game_sub_brand_id = {
        '全部游戏': 0,
        '角色扮演': 902032,
        '休闲益智': 902043,
        '经营策略': 902060,
        '体育竞速': 902095,
        '动作射击': 902122,
        '棋牌桌游': 902117
    }

    aes_params = {}
    cookie_status = True
    ddDataSpider = DdDataSpider()

    def generate_aes_params(self, brand_id):
        # 初始化aes加密参数
        self.aes_params = self.ddDataSpider.get_aes_param(
            # url=f'https://app.diandian.com/rank/android/2-{brand_id}-0-75-0',
            # headers=self.aes_headers,
            # params={
            #     'time': return_timestamp(),
            #     'timetype': 'custom'
            # },
            # proxies_type=True
            url=f'https://static.diandian.com/_app/app~dd2ce1b5.d39ea9a.js',
            headers=self.aes_headers,
            proxies_type=True
        )

    def get_cookies(self):
        cookies_dict = hgetall(self.ddDataSpider.COOKIE_REDIS_KEY)
        if not cookies_dict or not self.cookie_status:
            cookies = DdLogin().generate_cookie()
            return cookies
        else:
            email, cookies = random.choice(list(cookies_dict.items()))
            return json.loads(cookies)

    def generate_params(self, page, brand_id, sub_brand_id):
        params = {
            'market_id': '2',
            'genre_id': '0',
            'country_id': '75',
            'device_id': '0',
            'page': str(page),
            'time': return_timestamp(digit=10),
            'rank_type': '1',
            'brand_id': str(brand_id),
            'sub_brand_id': str(sub_brand_id),
        }
        aes_param = self.aes_params | {"d": 0, "sort": "dd", "num": 10}

        k = self.ddDataSpider.generate_k(
            e=params,
            path='/v1/rank',
            n=aes_param,
            r='get'
        )
        params = params | {'k': k}
        return params

    def start_requests(self):
        for brand_name, brand_id in self.brand_id.items():
            self.generate_aes_params(brand_id)
            sub_brand_id = self.app_sub_brand_id if brand_name == '应用' else self.game_sub_brand_id
            for sub_brand_name, sub_brand_id in sub_brand_id.items():
                for page in range(self.start_page, self.end_page + 1):
                    yield from self.get_list(brand_name, brand_id, sub_brand_name, sub_brand_id, page)

    def get_list(self, brand_name, brand_id, sub_brand_name, sub_brand_id, page):
        self.log_info(f'{self.name} 列表执行 brand:{brand_name} sub_brand:{sub_brand_name} page:{page}')
        params = self.generate_params(page, brand_id, sub_brand_id)
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
            try:
                yield from self.parse_list(response, brand_name, sub_brand_name)
            except Exception as e:
                msg = f'{self.name} 列表页解析错误: {e}, response: {response.json()}'
                self.log_error(msg)
                # send_dd_msg(self.name, '解析失败', msg)

    def parse_list(self, response, brand_name, sub_brand_name):
        result = response.json()
        if result.get('code') == 9 or result.get('msg') == "尚未登录" or result.get('msg') == '当前账号同时登录的设备数超限':
            logger.warning(f'{self.name} 请求异常, cookie_status设置为 False')
            self.cookie_status = False
        else:
            data = result.get('data')
            if data and isinstance(data, dict):
                apps = data['apps']
                ranks = data['ranks'][0]['apps']

                for app in apps:
                    en_app_id = app['id']
                    app_name = app['name']  # app名称
                    logo = app['logo']  # app logo
                    release_time = app['last_release_time']
                    developer = app['developer']['name']
                    rating = app['rating']  # 评分
                    rating_count = app.get('rating_count')  # 评分数
                    release_date = str(timestamp_to_datetime(release_time).date())  # 更新时间

                    md5_value = hash_md5(brand_name + sub_brand_name + app_name + release_date)

                    # item = APPListItem()
                    items = {}
                    items['rank_name'] = brand_name
                    items['sub_brand_name'] = sub_brand_name
                    items['en_app_id'] = en_app_id
                    items['app_name'] = app_name
                    items['logo'] = logo
                    items['release_date'] = release_date
                    items['developer'] = developer
                    items['rating'] = rating
                    items['rating_count'] = rating_count
                    items['platform'] = 'android'
                    items['md5_value'] = md5_value
                    # insert_data('app_list', item)
                    items['_table'] = 'app_list'
                    yield items

                # for rank in ranks:
                #     en_app_id = rank['id']
                #     total_ranking = rank['total_ranking']  # 总榜排行
                #     temp = {
                #         'total_ranking': total_ranking,
                #         'unique_value': en_app_id
                #     }
                #     update_data('app_list', temp, condition=f'en_app_id="{en_app_id}"')

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')