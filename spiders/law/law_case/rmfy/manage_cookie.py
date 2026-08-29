from utils.db.redis_opt import exist_key, hash_exists, hgetall
from utils.cookies_pool import ManageCookies
from loguru import logger
from spiders.law.law_case.rmfy.generate_cookie import GenerateCookie


class ManageLawCaseCookies(ManageCookies):
    spider_name = 'law_case'

    @staticmethod
    def random_crawl_time():
        return {'am': 8, 'pm': 20}

    def generate_cookie_pool(self):
        # 账号池不存在
        if not exist_key(self.account_pool_key):
            account_dict = hgetall(self.account_info_key)
            self.init_account_pool(account_dict, max_req_num=150)

        # 获取账号池账号配置信息
        account_pool = self.get_all(self.account_pool_key)
        for account in account_pool:
            phone = account['phone']
            password = account['password']
            # 判断账号生成的cookie是否存在
            if not hash_exists(self.cookies_pool_key, phone):
                # 账号cookie不存在，进入生成cookie逻辑
                # 生成cookie逻辑，首先检查账号是否满足使用条件
                if self.checkout_account(account, holiday_crawl=True):
                    cookie = GenerateCookie().main(phone, password)
                    if cookie:
                        logger.debug(f'phone:{phone} cookie初始化 cookie:{cookie}')
                        cookie_conf = self.init_cookie_conf(phone, cookie)
                        self.add_cookie_pool(phone, cookie_conf)

    def get_cookie(self):
        cookie_list = self.get_all(self.cookies_pool_key)
        if cookie_list:
            return self.random_cookie(cookie_list, lifetime=60*60*3)
        return None
