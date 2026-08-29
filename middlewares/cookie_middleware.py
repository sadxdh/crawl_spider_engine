"""
Cookie 注入中间件
读取 spider.use_cookie / spider.cookie_platform / spider.cookie_pool_type
"""
import json
import random
from loguru import logger
from utils.redis_client import get_redis
from config import COOKIES_POOL_REDIS_KEY


class CookieInjectMiddleware:
    """从 Redis Cookie 池获取并注入 Cookie"""

    def process_request(self, request, spider):
        use_cookie = getattr(spider, 'use_cookie', 0)
        if not use_cookie or int(use_cookie) == 0:
            return

        platform = getattr(spider, 'cookie_platform', spider.name)
        pool_type = getattr(spider, 'cookie_pool_type', 'hash')

        cookie_str = self._get_cookie(platform, pool_type)
        if not cookie_str:
            logger.warning(f"[CookieMiddleware] {spider.name} Cookie池为空: {platform}")
            return

        try:
            cookie_data = json.loads(cookie_str) if isinstance(cookie_str, str) else cookie_str
            if isinstance(cookie_data, dict):
                request.cookies = cookie_data
            else:
                request.headers['Cookie'] = str(cookie_str)
        except Exception as e:
            logger.warning(f"[CookieMiddleware] Cookie解析失败: {e}")
            request.headers['Cookie'] = str(cookie_str)

    def _get_cookie(self, platform: str, pool_type: str) -> str | None:
        r = get_redis()
        key = COOKIES_POOL_REDIS_KEY.format(platform)
        try:
            if pool_type == 'hash':
                fields = r.hkeys(key)
                if not fields:
                    return None
                return r.hget(key, random.choice(fields))
            elif pool_type == 'list':
                return r.lmove(key, key, 'LEFT', 'RIGHT')
        except Exception as e:
            logger.error(f"[CookieMiddleware] 获取Cookie失败: {e}")
        return None
