"""
企业预警通（qyyjt.cn）Token 管理器
功能：
  - 维护 Redis 内的账号池与 token 池
  - 自动登录（含验证码解析）、刷新 token
  - 对外只暴露 get_token() 接口，供各 qyyjt spider 调用

Redis key：
  qyyjt:account_pool  — hash，field=phone，value=account_info JSON
  qyyjt:token_pool    — hash，field=phone，value=token_info JSON
  qyyjt:account_info  — hash，field=phone，value=password（由运维写入）
"""
import hashlib
import json
import random
import time
from datetime import datetime

import requests
from loguru import logger
from retrying import retry

from config import ACCOUNT_POOL_REDIS_KEY as _KEY_TPL
from utils.redis_client import get_redis
from utils.admin_account_client import account_client
from utils.dingtalk import send_dd_msg

_ACCOUNT_POOL_KEY  = 'qyyjt:account_pool'
_TOKEN_POOL_KEY    = 'qyyjt:token_pool'
_ACCOUNT_INFO_KEY  = 'qyyjt:account_info'

_PIC_HEADERS = {
    'accept': '*/*',
    'accept-language': 'zh-CN,zh;q=0.9',
    'client': 'pc-web;pro',
    'dataid': '570',
    'referer': 'https://www.qyyjt.cn/user/login',
    'system1': 'Windows NT 10.0; Win64; x64;Chrome;128.0.0.0',
    'terminal': 'pc-web;pro',
    'user-agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/128.0.0.0 Safari/537.36'
    ),
    'ver': '20240827',
}

_LOGIN_HEADERS = {
    'accept': 'application/json',
    'accept-language': 'zh-CN,zh;q=0.9',
    'client': 'pc-web;pro',
    'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
    'dataid': '2',
    'origin': 'https://www.qyyjt.cn',
    'referer': 'https://www.qyyjt.cn/user/login',
    'system': 'new',
    'terminal': 'pc-web;pro',
    'user-agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/127.0.0.0 Safari/537.36'
    ),
    'ver': '20240718',
}

_BASE_URL    = 'https://www.qyyjt.cn/getData.action'
_REFRESH_URL = 'https://www.qyyjt.cn/refresh.action'

# token 有效时长（秒），超出后主动刷新
_TOKEN_TTL = 60 * 10


# ─────────────────────────────────────────────────────────────
# 内部辅助：验证码解析（调用 node 服务或本地 OCR，沿用旧逻辑占位）
# ─────────────────────────────────────────────────────────────
def _captcha_parse(image_content: bytes) -> str:
    """调用验证码识别服务，返回识别文字。"""
    try:
        from utils.node_client import NodeClient
        client = NodeClient()
        return client.captcha_parse(image_content)
    except Exception as e:
        logger.error(f'[qyyjt_token] 验证码解析失败: {e}')
        return ''


# ─────────────────────────────────────────────────────────────
# GenerateToken — 负责登录 / 刷新
# ─────────────────────────────────────────────────────────────
class _GenerateToken:

    @retry(stop_max_attempt_number=3)
    def _get_code_pic(self):
        resp = requests.get(_BASE_URL, headers=_PIC_HEADERS, timeout=15)
        result = resp.json()
        import base64
        image_base64 = result['data'].split(',')[1]
        image_content = base64.b64decode(image_base64)
        image_check_code = resp.headers['imageCheckCode']
        return image_content, image_check_code

    def _login(self, phone: str, password: str, image_check_code: str, image_content: bytes):
        captcha = _captcha_parse(image_content)
        data = {
            'phone': phone,
            'password': password,
            'imageCheckCode': image_check_code,
            'validatecode': captcha,
        }
        resp = requests.post(_BASE_URL, headers=_LOGIN_HEADERS, data=data, timeout=30)
        result = resp.json()
        user         = result['data']['basic_info']['user']
        token_data   = result['data']['token']
        access_token  = token_data['accessToken']
        refresh_token = token_data['refreshToken']
        return access_token, refresh_token, user

    def login_main(self, phone: str, password: str):
        logger.debug(f'[qyyjt_token] phone={phone} 登录开始')
        try:
            image_content, image_check_code = self._get_code_pic()
            md5_pwd = hashlib.md5(str(password).encode()).hexdigest()
            access_token, refresh_token, user = self._login(
                phone, md5_pwd, image_check_code, image_content
            )
            return {
                'phone': phone,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': user,
            }
        except Exception as e:
            return f'phone:{phone} {e}'

    @staticmethod
    def refresh_main(token: dict):
        phone         = token['phone']
        user          = token['user']
        refresh_token = token['refresh_token']
        params = {'time': str(int(time.time() * 1000)), 'terminal': 'web'}
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://www.qyyjt.cn/',
            'authorization': refresh_token,
            'client': 'pc-web;pro',
            'system': 'new',
            'terminal': 'pc-web;pro',
            'user': user,
            'user-agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/127.0.0.0 Safari/537.36'
            ),
        }
        try:
            resp = requests.get(_REFRESH_URL, headers=headers, params=params, timeout=15)
            data = resp.json()['data']
            return {
                'phone': phone,
                'user': user,
                'access_token': data['accessToken'],
                'refresh_token': data['refreshToken'],
            }
        except Exception as e:
            logger.error(f'[qyyjt_token] phone={phone} 刷新 token 失败: {e}')
            return None


# ─────────────────────────────────────────────────────────────
# ManageToken — 对外接口
# ─────────────────────────────────────────────────────────────
class ManageToken:
    """
    qyyjt token 池管理。
    用法：
        token = ManageToken().get_token()
        if token:
            headers['Pcuss'] = token['access_token']
            headers['User']  = token['user']
    """
    _SPIDER_NAME = 'qyyjt_token_manage'

    def __init__(self):
        self._redis = get_redis()
        self._gen   = _GenerateToken()

    # ── 内部工具 ───────────────────────────────────────────

    def _hget(self, key: str, field: str):
        raw = self._redis.hget(key, field)
        return json.loads(raw) if raw else {}

    def _hset(self, key: str, field: str, value):
        self._redis.hset(key, field, json.dumps(value))

    def _hdel(self, key: str, field: str):
        self._redis.hdel(key, field)

    def _hvals(self, key: str):
        vals = self._redis.hvals(key)
        return [json.loads(v) for v in vals] if vals else []

    def _hgetall(self, key: str):
        raw = self._redis.hgetall(key)
        return {k: v for k, v in raw.items()}

    @staticmethod
    def _now_date() -> int:
        return int(datetime.now().strftime('%Y%m%d'))

    @staticmethod
    def _now_ts() -> int:
        return int(datetime.now().timestamp())

    @staticmethod
    def _now_hour() -> int:
        return datetime.now().hour

    @staticmethod
    def _is_weekend() -> bool:
        return datetime.now().weekday() in (5, 6)

    # ── 账号池 ─────────────────────────────────────────────

    def _ensure_account_pool(self):
        """从平台 Admin API 获取账号/令牌，初始化账号池（仅首次）。"""
        if self._redis.exists(_ACCOUNT_POOL_KEY):
            return
        # 1. 优先从 Admin API 获取现成令牌（无需账号密码）
        cred = account_client.acquire('qyyjt')
        if cred and cred.get('access_token'):
            phone = cred.get('phone', 'auto')
            logger.warning(f'[qyyjt_token] Admin API获取令牌成功 phone={phone}')
            self._hset(_ACCOUNT_POOL_KEY, phone, {
                'phone': phone, 'password': '',
                'date': self._now_date(), 'count': 0,
                'max_req_num': 1000,
                'start_crawl_time': {'am': 0, 'pm': 23}, 'status': 1,
            })
            self._hset(_TOKEN_POOL_KEY, phone, cred)
            return
        # 2. 兜底：从 Admin API 获取账号列表
        accounts = account_client.get_accounts('qyyjt')
        if accounts:
            logger.warning(f'[qyyjt_token] Admin API账号 {len(accounts)} 个')
            for acc in accounts:
                phone = acc.get('phone', '')
                if not phone or self._hget(_ACCOUNT_POOL_KEY, phone):
                    continue
                self._hset(_ACCOUNT_POOL_KEY, phone, {
                    'phone': phone, 'password': acc.get('password', ''),
                    'date': self._now_date(), 'count': 0,
                    'max_req_num': acc.get('max_req_num', 100),
                    'start_crawl_time': {'am': 9, 'pm': 18}, 'status': 1,
                })
            return
        # 3. 最终兜底：Redis本地
        account_info = self._hgetall(_ACCOUNT_INFO_KEY)
        logger.warning(f'[qyyjt_token] Redis兜底 {len(account_info)} 个账号')
        for phone, password in account_info.items():
            if not self._hget(_ACCOUNT_POOL_KEY, phone):
                self._hset(_ACCOUNT_POOL_KEY, phone, {
                    'phone': phone, 'password': password,
                    'date': self._now_date(), 'count': 0,
                    'max_req_num': 100,
                    'start_crawl_time': {'am': 9, 'pm': 18}, 'status': 1,
                })

    def _reset_account(self, phone: str):
        account = self._hget(_ACCOUNT_POOL_KEY, phone)
        if account:
            account.update({
                'date': self._now_date(),
                'count': 0,
                'status': 1,
                'start_crawl_time': {'am': random.randint(8, 17), 'pm': 18},
            })
            self._hset(_ACCOUNT_POOL_KEY, phone, account)

    def _inc_account_count(self, phone: str) -> bool:
        account = self._hget(_ACCOUNT_POOL_KEY, phone)
        if account and account['count'] < account['max_req_num']:
            account['count'] += 1
            self._hset(_ACCOUNT_POOL_KEY, phone, account)
            return True
        return False

    # ── token 池 ───────────────────────────────────────────

    def _ensure_token_pool(self):
        """确保 token 池非空，必要时登录生成 token。"""
        self._ensure_account_pool()

        if self._redis.exists(_TOKEN_POOL_KEY):
            return

        for account in self._hvals(_ACCOUNT_POOL_KEY):
            phone    = account['phone']
            password = account['password']
            date     = account['date']
            count    = account['count']
            status   = account['status']
            start_crawl_time = account['start_crawl_time']

            if self._is_weekend():
                continue
            if self._now_date() > date:
                self._reset_account(phone)
            if status == 0 or count >= account['max_req_num']:
                continue

            am = start_crawl_time['am']
            pm = start_crawl_time['pm']
            if am <= self._now_hour() <= pm:
                result = self._gen.login_main(phone, password)
                if isinstance(result, dict):
                    result['timestamp'] = self._now_ts()
                    self._hset(_TOKEN_POOL_KEY, phone, result)
                elif isinstance(result, str):
                    msg = result.replace("'", '').replace('\n', '')
                    if any(kw in msg for kw in ('您的账号访问异常', '账号近期存在异常活动')):
                        self._hget(_ACCOUNT_POOL_KEY, phone)
                        acct = self._hget(_ACCOUNT_POOL_KEY, phone)
                        acct['status'] = 0
                        self._hset(_ACCOUNT_POOL_KEY, phone, acct)
                        send_dd_msg(
                            spider_name=self._SPIDER_NAME,
                            msg_name='账号异常',
                            msg_content=msg,
                            developer='',
                        )
                    elif '账号或密码输入错误' in msg:
                        self._hdel(_ACCOUNT_POOL_KEY, phone)
                        send_dd_msg(
                            spider_name=self._SPIDER_NAME,
                            msg_name='账号异常',
                            msg_content=msg,
                            developer='',
                        )

    # ── 公共接口 ───────────────────────────────────────────

    def get_token(self) -> dict | None:
        """
        获取一个可用 token dict：{'phone', 'access_token', 'refresh_token', 'user'}
        若暂无可用 token 返回 None。
        """
        token_list = self._hvals(_TOKEN_POOL_KEY)
        if not token_list:
            self._ensure_token_pool()
            return None

        token = random.choice(token_list)
        phone = token['phone']

        if not self._inc_account_count(phone):
            logger.warning(f'[qyyjt_token] phone={phone} 今日请求次数已耗尽')
            self._hdel(_TOKEN_POOL_KEY, phone)
            return None

        if self._now_ts() - token.get('timestamp', 0) <= _TOKEN_TTL:
            return token

        # token 过期，尝试刷新
        new_token = self._gen.refresh_main(token)
        if new_token:
            new_token['timestamp'] = self._now_ts()
            self._hset(_TOKEN_POOL_KEY, phone, new_token)
            logger.info(f'[qyyjt_token] phone={phone} 刷新 token 成功')
            return new_token

        logger.warning(f'[qyyjt_token] phone={phone} 刷新失败，删除旧 token')
        self._hdel(_TOKEN_POOL_KEY, phone)
        return None
