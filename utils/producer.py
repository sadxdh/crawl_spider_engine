"""
任务生产者 - 向 Redis 队列推送爬虫任务
参考: yuncrawl/crawl/core/producer.py
兼容现有 yuncrawl_task:{spider_type} 格式
"""
import json
from datetime import datetime
from loguru import logger
from utils.redis_client import get_redis
from config import TASK_QUEUE_KEY


def push_task(spider_name: str, spider_type: str, task_params: dict = None) -> str:
    """
    向 Redis 队列推送单个爬虫任务

    Args:
        spider_name: 爬虫名称
        spider_type: 爬虫类型（决定队列名）
        task_params: 额外任务参数

    Returns:
        队列 Key
    """
    r = get_redis()
    queue_key = TASK_QUEUE_KEY.format(spider_type)

    task = {
        'spider_name': spider_name,
        'spider_type': spider_type,
        'schedule_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        **(task_params or {}),
    }

    r.rpush(queue_key, json.dumps(task, ensure_ascii=False))
    logger.info(f"[Producer] 任务已推送: {spider_name} -> {queue_key}")
    return queue_key


def push_task_list(project_list: list[dict]) -> int:
    """
    批量推送任务列表
    参考: yuncrawl/crawl/core/producer.py push_task_to_redis()

    project_list 格式:
    [
        {'spider_name': 'chanquan', 'spider_type': 'economy', ...},
        {'spider_name': 'finance_bond', 'spider_type': 'finance', ...},
    ]
    """
    r = get_redis()
    count = 0

    for project in project_list:
        spider_type = project.get('spider_type', 'other')
        queue_key = TASK_QUEUE_KEY.format(spider_type)

        task = {
            'schedule_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            **project,
        }
        r.rpush(queue_key, json.dumps(task, ensure_ascii=False))
        count += 1

    logger.info(f"[Producer] 批量推送完成: {count} 个任务")
    return count


def get_queue_length(spider_type: str) -> int:
    """获取指定类型队列的任务数"""
    r = get_redis()
    return r.llen(TASK_QUEUE_KEY.format(spider_type))


def clear_queue(spider_type: str) -> int:
    """清空指定类型队列"""
    r = get_redis()
    key = TASK_QUEUE_KEY.format(spider_type)
    length = r.llen(key)
    r.delete(key)
    logger.warning(f"[Producer] 队列已清空: {key} ({length} 个任务)")
    return length
