# 点点数据登录,获取cookie保存信息
import math
import os
from utils.db.redis_opt import *
from spiders.economy.app_info.dd_data import DdDataSpider
from utils.decrypt import decrypt_diandian_data_spider
from utils.tools import *
from loguru import logger


class DdLogin(DdDataSpider):
    spider_name = 'app_info_dd_login'
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Content-Type': 'application/json',
        'Origin': 'https://app.diandian.com',
        'Pragma': 'no-cache',
        'Referer': 'https://app.diandian.com/',
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        'language': 'zh',
        'platform': '3',
    }

    def __init__(self, **kwargs):
        super().__init__()
        self.session = requests.Session()
        self.session.proxies = get_seesion_proxies()

    def get_param(self):
        # 获取aes参数
        params = self.get_aes_param(
            session=self.session,
            url='https://static.diandian.com/_app/app~dd2ce1b5.d39ea9a.js',
            headers=self.headers,
            method='GET',
        )
        return params

    @staticmethod
    def generate_data(account, password, aes_param):
        # 根据参数生成加密k
        json_data = {'email': account, 'password': password}
        aes_param.update({'d': 0, 'sort': 'dc', 'num': 10})
        k = decrypt_diandian_data_spider(
            e=json_data,
            path="/v1/user/company/login",
            n=aes_param,
            r='post'
        )
        json_data.update({'k': k})
        return json_data

    def get_deviceid(self, t):
        return os.urandom(math.ceil(t / 2)).hex()[:t]

    def login(self, data):
        # 登录
        self.session.cookies['deviceid'] = self.get_deviceid(31)
        response = self.session.request(
            url='https://api.diandian.com/pc/common/v1/user/company/login',
            method='POST',
            headers=self.headers,
            json=data
        )
        if response:
            cookies = self.session.cookies.get_dict()
            try:
                result = response.json()
                token = result['data']['token']
                cookies = cookies | {'token': token}
                return cookies
            except Exception as e:
                msg = f'{self.spider_name} 登录解析token失败, e:{e}, response:{response.text}'
                logger.error(msg)
                # send_dd_msg(self.spider_name, '解析失败', msg)
        return None

    def generate_cookie(self):
        cookies = {}
        account_dict = hgetall(self.ACCOUNT_REDIS_KEY)
        for account, password in account_dict.items():
            logger.debug(f'正在登录：{account}')
            aes_param = self.get_param()
            data = self.generate_data(account.decode('utf-8'), password.decode('utf-8'), aes_param)
            cookies = self.login(data)
            logger.debug(f'cookie存储到redis cookies：{cookies}')
            hset(self.COOKIE_REDIS_KEY, account, json.dumps(cookies))
        return cookies

