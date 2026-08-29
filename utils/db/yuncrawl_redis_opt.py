import redis
from config import REDIS_CONF

class RedisConnectPool:
    _isinstance = None

    def __new__(cls, *args, **kwargs):
        if cls._isinstance is None:
            cls._isinstance = super().__new__(cls)
        return cls._isinstance

    def __init__(self):
        self.redis_pool = redis.ConnectionPool(max_connections=30, **REDIS_CONF)

    def get_redis_conn(self):
        return redis.Redis(connection_pool=self.redis_pool)

redis_pool = RedisConnectPool()



# redis数据库装饰器
def redis_wrap(func):
    def wrapper(*args, **kwargs):
        connection = kwargs.get('conn', redis_pool.get_redis_conn())
        try:
            result = func(connection, *args, **kwargs)
            connection.close()
        except Exception as e:
            raise e
        return result

    return wrapper


@redis_wrap
def exist_key(conn, key):
    return conn.exists(key)


@redis_wrap
def scan_keys(conn, keyword):
    cursor = 0
    while True:
        cursor, keys = conn.scan(cursor, match=f'*{keyword}*', count=10000)
        if cursor == 0:
            return keys


@redis_wrap
def delete_key(conn, key):
    return conn.delete(key)


@redis_wrap
def set_expire(conn, key, timestamp):
    conn.expire(key, timestamp)  # 设置到达时间戳时过期


@redis_wrap
def increment_count(conn, key):
    return conn.incr(key)


@redis_wrap
def init_increment(conn, key):
    conn.set(key, 0)  # 设置初始计数器值


@redis_wrap
def get_increment(conn, key):
    value = conn.get(key)
    return int(value) if value else 0


# hash
@redis_wrap
def hset(conn, key, field, value):
    return conn.hset(key, field, value)


@redis_wrap
def hget(conn, key, field):
    return conn.hget(key, field)


@redis_wrap
def hgetall(conn, key):
    return conn.hgetall(key)


@redis_wrap
def hdel(conn, key, field):
    conn.hdel(key, field)


@redis_wrap
def hlen(conn, key):
    return conn.hlen(key)


@redis_wrap
def hvals(conn, key) -> list:
    return conn.hvals(key)


@redis_wrap
def hkeys(conn, key) -> list:
    return conn.hkeys(key)


# list
@redis_wrap
def lpush(conn, key, value):
    return conn.lpush(key, value)


@redis_wrap
def rpush(conn, key, value):
    return conn.rpush(key, value)


@redis_wrap
def lrange(conn, key, start, end):
    return conn.lrange(key, start, end)


@redis_wrap
def lpop(conn, key):
    return conn.lpop(key)


# 集合
@redis_wrap
def sister_member(conn, key, value):
    return conn.sismember(name=key, value=value)


# 字符

@redis_wrap
def str_set(conn, key, value):
    return conn.set(name=key, value=value)


@redis_wrap
def str_get(conn, key):
    return conn.get(name=key)
