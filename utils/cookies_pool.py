from utils.db.redis_opt import *
from config import ACCOUNT_POOL_REDIS_KEY, ACCOUNT_INFO_REDIS_KEY, COOKIES_POOL_REDIS_KEY
from utils.tools import *
from utils.time_kit import *
from typing import Dict

class ManageCookies:
    """管理Cookie池和账号池的类"""
    spider_name = 'cookies'

    def __init__(self):
        self.account_info_key = ACCOUNT_INFO_REDIS_KEY.format(self.spider_name)
        self.account_pool_key = ACCOUNT_POOL_REDIS_KEY.format(self.spider_name)
        self.cookies_pool_key = COOKIES_POOL_REDIS_KEY.format(self.spider_name)

    @staticmethod
    def get_all(key):
        result = hvals(key)
        return [deserialize(i) for i in result] if result else []

    @staticmethod
    def get_one(key, field):
        data = hget(key, field)
        return deserialize(data)

    def add_account_pool(self, phone, value):
        hset(self.account_pool_key, phone, serialize(value))

    def add_cookie_pool(self, phone, value):
        hset(self.cookies_pool_key, phone, serialize(value))

    @staticmethod
    def is_holiday():
        """判断当天是否为工作日"""
        weekday = datetime.now().weekday()
        return True if weekday in [5, 6] else False

    @staticmethod
    def random_crawl_time():
        return {'am': random.randint(6, 12), 'pm': random.randint(18, 20)}

    def init_account_pool(self, account_dict:dict, max_req_num=10):
        #  初始化账号池，将为每个账号进行配置、
        for phone, password in account_dict.items():
            if not hash_exists(self.account_pool_key, phone):
                conf = {
                    'phone': phone,
                    'password': password,
                    'date': return_today('%Y%m%d'),
                    'count': 0,
                    'max_req_num': max_req_num,
                    'start_crawl_time': self.random_crawl_time(),
                    'status': 1
                }
                self.add_account_pool(phone, conf)

    def update_account_count(self, phone):
        # 更新账号请求次数
        account = self.get_one(self.account_pool_key, phone)
        if account and account['count'] < account['max_req_num']:
            account['count'] += 1
            self.add_account_pool(phone, account)
            logger.info(f'phone:{phone} 请求次数：{account["count"]} 次')
            return True
        return False

    def update_account_conf(self, phone):
        # 更新账号配置
        account = self.get_one(self.account_pool_key, phone)
        if account:
            new_params = {
                'date': return_today('%Y%m%d'),
                'count': 0,
                'status': 1,
                'start_crawl_time': self.random_crawl_time()
            }
            account.update(new_params)
            self.add_account_pool(phone, account)

    def update_account_status(self, phone, status):
        # 更新账号状态, 1:可用 0:不可用
        account = self.get_one(self.account_pool_key, phone)
        if account:
            account['status'] = status
            self.add_account_pool(phone, account)

    @staticmethod
    def init_cookie_conf(phone: [str, int], cookie):
        return {'phone': phone, 'cookie': cookie, 'timestamp': int(return_timestamp(10))}

    @staticmethod
    def _is_crawl_time(crawl_time: Dict[str, int]) -> bool:
        """判断当前是否在爬取时间范围内"""
        now_hour = datetime.now().hour
        return crawl_time['am'] <= now_hour <= crawl_time['pm']

    def _should_not_crawl(self, account: Dict, holiday_crawl: bool) -> bool:
        """判断是否应该跳过爬取"""
        return (
                (self.is_holiday() and not holiday_crawl) or
                (account['status'] == 0) or
                (account['count'] >= account['max_req_num'])
        )

    def checkout_account(self, account: dict, holiday_crawl=False):
        # 获取账号池账号配置信息
        phone = account['phone']
        date = account['date']
        start_crawl_time = account['start_crawl_time']

        # 当前日期大于账号池日期,更新账号状态
        if return_today('%Y%m%d') > date:
            self.update_account_conf(phone)

        # 检查爬取条件, 返回True为不可用
        if self._should_not_crawl(account, holiday_crawl):
            return False

        # 当前时间在爬取时间(9-18点)内
        if not self._is_crawl_time(start_crawl_time):
            return False
        return True

    def random_cookie(self, cookie_list, lifetime=60 * 60):
        cookie = random.choice(cookie_list)
        phone = cookie['phone']
        update_status = self.update_account_count(phone)
        if not update_status:
            logger.warning(f'phone:{phone} 今日设置的请求次数已用完')
            hdel(self.cookies_pool_key, phone)

        if int(return_timestamp(10)) - cookie['timestamp'] > lifetime:
            logger.warning(f'phone:{phone} cookie存在超过{lifetime}秒')
            hdel(self.cookies_pool_key, phone)
        return cookie
