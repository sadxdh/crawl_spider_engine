"""
账号池管理器 — 从 Redis DB1 读取旧平台账号，规范化提供给爬虫
不做写操作，仅读取已有账号/令牌/cookie

Redis DB1 结构:
  <platform>:account_info  hash → {phone: password}
  <platform>:account_pool  hash → {phone: '{...json status...}'}
  <platform>:token_pool    hash → {phone: '{...json token...}'}
  <platform>:cookie_pool   hash → {phone: '{...json cookie...}'}
"""
import json
import random
from typing import Optional

import redis as _redis

from config import get_config

_conn = None


def _get_redis():
    global _conn
    if _conn is None:
        conf = get_config('dev')
        redis_cfg = conf.get('REDIS', {})
        _conn = _redis.Redis(
            host=redis_cfg.get('host', 'py.w.com'),
            password=redis_cfg.get('password', ''),
            port=int(redis_cfg.get('port', 6379)),
            db=1,  # 旧平台账号数据在 DB1
            decode_responses=True,
            socket_connect_timeout=5,
        )
    return _conn


class AccountPool:
    """单个平台的账号池"""

    def __init__(self, platform: str):
        self.platform = platform
        self._r = _get_redis()

    @property
    def info_key(self) -> str:
        return f'{self.platform}:account_info'

    @property
    def pool_key(self) -> str:
        return f'{self.platform}:account_pool'

    @property
    def token_key(self) -> str:
        return f'{self.platform}:token_pool'

    @property
    def cookie_key(self) -> str:
        return f'{self.platform}:cookie_pool'

    def get_accounts(self) -> dict:
        """获取所有账号 {phone: password}"""
        try:
            return self._r.hgetall(self.info_key) or {}
        except Exception:
            return {}

    def get_random_account(self) -> tuple:
        """随机获取一个账号 (phone, password)"""
        accounts = self.get_accounts()
        if not accounts:
            return None, None
        phone = random.choice(list(accounts.keys()))
        return phone, accounts[phone]

    def get_token(self, phone: str) -> Optional[str]:
        """获取指定账号的令牌"""
        try:
            data = self._r.hget(self.token_key, phone)
            if data:
                obj = json.loads(data)
                return obj.get('token') or obj.get('access_token') or obj.get('ticket')
        except Exception:
            pass
        return None

    def get_cookies(self, phone: str) -> Optional[dict]:
        """获取指定账号的 Cookie"""
        try:
            data = self._r.hget(self.cookie_key, phone)
            if data:
                return json.loads(data)
        except Exception:
            pass
        try:
            data = self._r.hget(self.token_key, phone)
            if data:
                obj = json.loads(data)
                if 'cookie' in obj:
                    return obj['cookie']
        except Exception:
            pass
        return None

    def get_token_for_any(self) -> Optional[str]:
        """获取任意可用账号的令牌"""
        try:
            tokens = self._r.hgetall(self.token_key) or {}
            if not tokens:
                return None
            phone = random.choice(list(tokens.keys()))
            return self.get_token(phone)
        except Exception:
            return None

    def get_cookies_for_any(self) -> Optional[dict]:
        """获取任意可用账号的 Cookie"""
        try:
            cookies = self._r.hgetall(self.cookie_key) or {}
            if not cookies:
                return None
            phone = random.choice(list(cookies.keys()))
            return self.get_cookies(phone)
        except Exception:
            return None


# 全局便捷访问
def get_account_pool(platform: str) -> AccountPool:
    return AccountPool(platform)
