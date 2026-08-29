"""
MySQL DBUtils 连接池单例
参考: data_crawl_server/crawl/db/db_conn.py
"""
import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB
from loguru import logger
from config import DB_CONF


class MysqlConnectPool:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._pool = PooledDB(
                creator=pymysql,
                mincached=1,
                maxcached=20,
                maxconnections=50,
                blocking=True,
                use_unicode=True,
                cursorclass=DictCursor,
                **DB_CONF,
            )
            logger.info(f"[MysqlPool] 初始化: {DB_CONF['host']}:{DB_CONF['port']} db={DB_CONF['database']}")
        return cls._instance

    def get_conn(self):
        return self._pool.connection()


mysql_pool = MysqlConnectPool()


def get_mysql():
    return mysql_pool.get_conn()
