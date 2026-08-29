# 账号登录
import requests

from utils.db.redis_opt import hgetall, hset
from utils.decrypt import decrypt_title_transaction_spider
from utils.tools import *

ACCOUNT_REDIS_KEY = 'title_transaction:account_info'
COOKIE_REDIS_KEY = 'title_transaction:cookie_pool'


class AccountLogin():
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://bigdata.cspea.com.cn',
        'Referer': 'https://bigdata.cspea.com.cn/cq/list?s=A01',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
        'X-Requested-With': 'XMLHttpRequest',
    }

    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.proxy_ip = ScrapyProxy.get_long_proxy()
        self.session.proxies = {
            "http": self.proxy_ip,
            "https": self.proxy_ip,
        }

    def hash_md5(self, str_content):
        m5 = md5()
        if isinstance(str_content, bytes):
            content = str_content
        else:
            content = str(str_content).encode("utf8")
        m5.update(content)
        content_md5 = m5.hexdigest()
        return content_md5

    def first_req(self, phone, password):
        data = {
            'authType': '0',
            'username': phone,
            'password': self.hash_md5(password),
        }
        response = self.session.post(url='https://bigdata.cspea.com.cn/zuul/auth/uaa/oauth/token',
                                    headers=self.headers,
                                    data=data)
        result = response.json()
        time_stamp = result['time']
        return time_stamp

    def get_user(self, phone):
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Referer': 'https://bigdata.cspea.com.cn/cq/list?s=A01',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
            'X-Requested-With': 'XMLHttpRequest',
        }

        params = {'authKey': phone}
        response = self.session.get(
            'https://bigdata.cspea.com.cn/zuul/user-manage/token-api/user/getUser',
            params=params,
            headers=headers,
        )
        result = response.text
        return result

    def login(self):
        account_dict = hgetall(ACCOUNT_REDIS_KEY)
        for phone, password in account_dict.items():
            logger.debug(f'正在登录：{phone}')
            time_stamp = self.first_req(phone, password)
            user_info = self.get_user(phone)
            cookies = self.session.cookies.get_dict()
            cookie = decrypt_title_transaction_spider(phone.decode("utf8", errors="ignore"), time_stamp, user_info)
            cookies.update(cookie)
            logger.debug(f'cookie存储到redis：{phone}')
            hset(COOKIE_REDIS_KEY, phone, json.dumps(cookies))
            return cookies
        return {}
