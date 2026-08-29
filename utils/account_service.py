"""
账号服务 — 从 Redis DB3 读取账号/令牌/cookie（已从旧平台DB1恢复）
提供统一接口给爬虫使用
"""
import json, random, threading
from typing import Optional

from utils.redis_client import get_redis


class AccountService:
    """账号池服务，从 Redis DB3 管理多平台账号/令牌/cookie"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._r = get_redis()
        return cls._instance

    @property
    def redis(self):
        return self._r

    # ─── 账号查询 ───────────────────────────────────────────

    def get_accounts(self, platform: str) -> dict:
        """获取平台所有账号 {phone/email: password}"""
        key = f'{platform}:account_info'
        try:
            return self.redis.hgetall(key) or {}
        except Exception:
            return {}

    def get_random_account(self, platform: str) -> tuple:
        """随机获取一个账号"""
        accounts = self.get_accounts(platform)
        if not accounts:
            return None, None
        ident = random.choice(list(accounts.keys()))
        return ident, accounts[ident]

    def get_account_pool(self, platform: str) -> dict:
        """获取账号池状态（含count/max_req_num等参数）"""
        key = f'{platform}:account_pool'
        try:
            raw = self.redis.hgetall(key) or {}
            return {k: (json.loads(v) if isinstance(v, str) and v.startswith('{') else v) for k, v in raw.items()}
        except Exception:
            return {}

    # ─── 令牌查询 ───────────────────────────────────────────

    def get_token(self, platform: str, phone: str = None) -> Optional[dict]:
        key = f'{platform}:token_pool'
        try:
            pool = self.redis.hgetall(key) or {}
            if phone and phone in pool:
                raw = pool[phone]
                return json.loads(raw) if isinstance(raw, str) else raw
            if pool:
                phone = random.choice(list(pool.keys()))
                raw = pool[phone]
                return json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            pass
        return None

    # ─── Cookie 查询 ────────────────────────────────────────

    def get_cookies(self, platform: str, phone: str = None) -> Optional[dict]:
        key = f'{platform}:cookie_pool'
        try:
            pool = self.redis.hgetall(key) or {}
            if phone and phone in pool:
                raw = pool[phone]
                return json.loads(raw) if isinstance(raw, str) else raw
            if pool:
                phone = random.choice(list(pool.keys()))
                raw = pool[phone]
                return json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            pass
        return None

    # ─── 特殊查询 ───────────────────────────────────────────

    def get_phone_pool(self, platform: str) -> list:
        key = f'{platform}:phone_pool'
        try:
            return list((self.redis.hgetall(key) or {}).keys())
        except Exception:
            return []

    def get_proxy_list(self) -> list:
        try:
            return self.redis.lrange('crawl_proxy:static_proxy', 0, -1) or []
        except Exception:
            return []

    def get_insert_counter(self, spider_name: str) -> int:
        key = f'insert_counter:{spider_name}'
        try:
            val = self.redis.get(key) or '0'
            return int(str(val))
        except (ValueError, TypeError):
            return 0


# 全局单例
account_service = AccountService()

