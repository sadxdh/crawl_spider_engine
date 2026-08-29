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
                        # mincached=1,
                        # maxcached=5,
                        use_unicode=True,
                        cursorclass=DictCursor,
                        **conf)
        return pool

    def get_mysql_conn(self):
        if not self.mysql_conn_pool:
            raise Exception("Mysql Connection pool is not initialized")
        return self.mysql_conn_pool.connection()

mysql_pool = MysqlConnectPool()


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




def select_data(table, data, condition=None, suffix=None, select_type='all', spider_name='', **kwargs):
    sql = ''
    datas = []
    try:
        filed = ','.join(data)
        condition_str = f'where {condition}' if condition else ''
        suffix_str = f" {suffix}" if suffix else ""
        sql = f'select {filed} from {table} {condition_str}{suffix_str}'
        datas = get_all(sql, **kwargs) if select_type == 'all' else get_one(sql, **kwargs)
        logger.info(f'Select sql successfully  nums: {len(datas) if datas else 0}')
    except Exception as e:
        error_msg = f'Select fail mysql: {e}, sql: {sql}'
        logger.error(error_msg)
        # send_dd_msg(spider_name, '数据查询失败', error_msg)
    return datas

def update_set(table, data, condition=None, **kwargs):
    """
    更新数据。

    :param table: 表名
    :param data: 要更新的字段，例如 {"status": 0}
    :param condition: 条件，例如 "user_id = '1701006109228367'"
    """
    sql = ""
    try:
        set_str = ", ".join(f"{field} = %s" for field in data)
        condition_str = f" WHERE {condition}" if condition else ""

        sql = f"UPDATE {table} SET {set_str}{condition_str}"
        affected_rows = execute_sql(sql, tuple(data.values()), **kwargs)

        logger.info(f"Update sql successfully, affected rows: {affected_rows}")
        return affected_rows

    except Exception as e:
        error_msg = f"Update fail mysql: {e}, sql: {sql}"
        logger.error(error_msg)
        return 0