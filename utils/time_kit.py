"""
时间工具函数
参考: yuncrawl/crawl/utils/time_kit.py
"""
from datetime import datetime, timedelta, date
import pandas as pd

FORMAT_DATE_STR = '%Y-%m-%d %H:%M:%S'


def timestamp_to_datetime(timestamp: (int, str)):
    """
    时间戳转日期
    :params timestamp
    """
    timestamp = str(timestamp)[:10]
    return datetime.fromtimestamp(int(timestamp))

def return_timestamp(digit=13):
    timestamp = str(datetime.timestamp(datetime.now())*1000).split('.')[0]
    return timestamp[:digit]

def now_str(fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """当前时间字符串"""
    return datetime.now().strftime(fmt)


def today_str(fmt: str = '%Y-%m-%d') -> str:
    """今日日期字符串"""
    return date.today().strftime(fmt)


def yesterday_str(fmt: str = '%Y-%m-%d') -> str:
    """昨日日期字符串"""
    return (date.today() - timedelta(days=1)).strftime(fmt)

def return_yesterday():
    """ 返回昨天日期 """
    return (datetime.today() - timedelta(days=1)).date()

def return_today(date_type='%Y-%m-%d %H:%M:%S'):
    """返回今天日期"""
    return datetime.today().strftime(date_type)

def return_tomorrow():
    """ 返回明天日期 """
    return (datetime.today() + timedelta(days=1)).date()


def date_range(start: str, end: str, fmt: str = '%Y-%m-%d') -> list[str]:
    """生成日期范围列表"""
    start_dt = datetime.strptime(start, fmt)
    end_dt = datetime.strptime(end, fmt)
    result = []
    cur = start_dt
    while cur <= end_dt:
        result.append(cur.strftime(fmt))
        cur += timedelta(days=1)
    return result


def parse_date(date_str: str) -> str:
    """尝试解析各种日期格式，统一返回 YYYY-MM-DD"""
    formats = [
        '%Y-%m-%d', '%Y/%m/%d', '%Y年%m月%d日',
        '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S',
        '%d/%m/%Y', '%m/%d/%Y',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return date_str  # 无法解析则原样返回


def timestamp_to_str(ts: int | float, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """时间戳转字符串"""
    return datetime.fromtimestamp(ts).strftime(fmt)


def generate_every_year_date(start_date, end_date):
    """生成每年的开始日期， 结束日期"""
    annual_year = [[datetime.strftime(x, '%Y-01-01'), datetime.strftime(x, '%Y-12-31')]
                   for x in list(pd.date_range(start=start_date, end=end_date, freq='YE'))]
    return annual_year


def generate_every_month_date(start_date, end_date):
    """
    生成每个月的开始日期和结束日期
    :param start_date: 起始日期，字符串格式，如 '2023-01-01'
    :param end_date: 结束日期，字符串格式，如 '2024-12-31'
    :return: 一个列表，每个元素是 [月开始日期, 月结束日期]，格式为字符串 'YYYY-MM-DD'
    """
    monthly_periods = pd.date_range(start=start_date, end=end_date, freq='ME')
    monthly_ranges = [
        [
            (period - pd.offsets.MonthBegin(1)).strftime('%Y-%m-%d'),  # 该月的第一天
            period.strftime('%Y-%m-%d')                               # 该月的最后一天
        ]
        for period in monthly_periods
    ]
    return monthly_ranges

def format_date(the_time, format_str='-') -> str:
    """
    日期格式化
    :param the_time:datetime类型
    :param format_str: 日期分隔符
    :return:
    """
    the_date = the_time.strftime("%Y{0}%m{0}%d".format(format_str))
    return the_date

def date_through(days: int, types: str = '-'):
    """
    获取过去的日期, 未来的日期
    :param days 正整数获取未来日期, 负整数获取过去的日期, o当天日期
    :param types 日期的分割符
    """
    if days < 0:
        date_past = datetime.today() - timedelta(days=abs(days))
        date = format_date(date_past, types)
    elif days > 0:
        date_future = datetime.today() + timedelta(days=days)
        date = format_date(date_future, types)
    else:
        date = format_date(datetime.now().date())
    return str(date)

def dispose_update_date(value):
    """处理更新时间"""
    return value.replace('年', '-').replace('月', '-').replace('日', '')

def format_datetime(the_time, format_str=FORMAT_DATE_STR) -> datetime:
    the_time = datetime.strptime(the_time, format_str)
    return the_time

def trans_en_date(value, format_str='%b %d, %Y'):
    """格式化英文日期"""
    date = datetime.strptime(value, format_str).date()
    return str(date)