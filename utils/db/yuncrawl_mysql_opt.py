import pymysql
from loguru import logger
from dbutils.pooled_db import PooledDB
from pymysql.cursors import DictCursor
from config import DB_CONF

class MysqlConnectPool:
    _isinstance = None

    def __new__(cls, *args, **kwargs):
        if cls._isinstance is None:
            cls._isinstance = super().__new__(cls)
        return cls._isinstance

    def __init__(self):
        self.mysql_conn_pool = self.creat_conn_pool(DB_CONF)

    @staticmethod
    def creat_conn_pool(conf):
        pool = PooledDB(creator=pymysql,
                        mincached=1,
                        maxcached=20,
                        use_unicode=True,
                        cursorclass=DictCursor,
                        **conf)
        return pool

    def get_mysql_conn(self):
        return self.mysql_conn_pool.connection()

mysql_pool = MysqlConnectPool()


# mysql数据库装饰器
def mysql_wrap(func):
    def wrapper(*args, **kwargs):
        connection = kwargs.get('conn', mysql_pool.get_mysql_conn())
        try:
            cursor = connection.cursor()
            result = func(cursor, *args)
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        return result

    return wrapper

@mysql_wrap
def table_exists(cursor, table_name):
    sql = f'SHOW TABLES LIKE "{table_name}"'
    return bool(cursor.execute(sql))


@mysql_wrap
def get_one(cursor, sql):
    cursor.execute(sql)
    return cursor.fetchone()


@mysql_wrap
def get_many(cursor, sql, num=10):
    cursor.execute(sql)
    return cursor.fetchmany(num)


@mysql_wrap
def get_all(cursor, sql, param=None):
    cursor.execute(sql, param)
    return cursor.fetchall()


@mysql_wrap
def execute_sql(cursor, sql, param=None):
    result = cursor.execute(sql, param)
    return result
