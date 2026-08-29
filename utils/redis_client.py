"""
Redis 连接池单例
参考: yuncrawl/crawl/db/db_conn.py
"""
import redis
from loguru import logger
from config import REDIS_CONF


class RedisConnectPool:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._pool = redis.ConnectionPool(
                host=REDIS_CONF['host'],
                port=REDIS_CONF['port'],
                password=REDIS_CONF.get('password'),
                db=REDIS_CONF['db'],
                max_connections=30,
                decode_responses=True,
                encoding='utf-8',
            )
            logger.info(f"[RedisPool] 初始化: {REDIS_CONF['host']}:{REDIS_CONF['port']} db={REDIS_CONF['db']}")
        return cls._instance

    def get_conn(self) -> redis.Redis:
        return redis.Redis(connection_pool=self._pool)


# 全局单例
redis_pool = RedisConnectPool()

# 账号池 Redis（DB1，存储旧平台账号/令牌/cookie）
import redis as _redis
from config import REDIS_CONF as _RC

_account_pool = _redis.ConnectionPool(
    host=_RC['host'],
    port=_RC['port'],
    password=_RC.get('password'),
    db=1,
    max_connections=10,
    decode_responses=True,
    encoding='utf-8',
)


def get_redis() -> _redis.Redis:
    return redis_pool.get_conn()


def get_account_redis() -> _redis.Redis:
    """获取账号池 Redis 连接（DB1：旧平台账号数据）"""
    return _redis.Redis(connection_pool=_account_pool)
