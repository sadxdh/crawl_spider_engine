"""Job 信息查询工具 — 爬虫启动时通过 Admin API 获取 Job 配置

使用方式：
    from utils.job_helper import get_job_info

    class MySpider(BaseSpider):
        def start_requests(self):
            info = get_job_info(self.name)
            self.job_id = info['job_id']
            self.data_table = info['data_table']
            # ...
"""

import os
import functools
import requests
from loguru import logger

ADMIN_URL = os.environ.get('ADMIN_API_URL', 'http://10.88.0.1:5000')
API_PREFIX = '/api/v1'
REQUEST_TIMEOUT = 10


@functools.lru_cache(maxsize=128)
def get_job_info(spider_name: str) -> dict:
    """
    根据爬虫名查询 Job 配置。
    结果被缓存，同一进程内多次调用不会重复请求。
    返回: { spider_name, job_id, data_table, business_name, cron_expr, ... }
    """
    url = f'{ADMIN_URL}{API_PREFIX}/spiders/{spider_name}/job-info'
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        data = resp.json()
        if data.get('code') == 0:
            info = data['data']
            logger.info(f'[JobHelper] {spider_name} → job_id={info.get("job_id")} '
                        f'table={info.get("data_table")}')
            return info
        else:
            logger.warning(f'[JobHelper] {spider_name} 查询失败: {data.get("message")}')
            return _default(spider_name)
    except Exception as e:
        logger.warning(f'[JobHelper] {spider_name} 接口不可达: {e}')
        return _default(spider_name)


def _default(spider_name: str) -> dict:
    return {
        'spider_name': spider_name,
        'job_id': 0,
        'display_name': spider_name,
        'data_table': '',
        'source_name': '',
        'source_url': '',
        'business_name': '',
        'job_name': '',
        'cron_expr': '',
        'developer': '',
    }


def clear_cache():
    """清除 job info 缓存（测试/调试用）"""
    get_job_info.cache_clear()
