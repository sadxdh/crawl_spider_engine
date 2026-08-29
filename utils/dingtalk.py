"""
钉钉机器人告警
参考: yuncrawl/crawl/utils/dingding.py
"""
import time
import hmac
import hashlib
import base64
import urllib.parse
import threading
import requests
from functools import wraps
from loguru import logger
from config import DINGTALK_CONF


_sent_cache: dict = {}
_cache_lock = threading.Lock()


def lock(interval: int = 10):
    """消息去重锁装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            now = time.time()
            with _cache_lock:
                if now - _sent_cache.get(key, 0) < interval:
                    return
                _sent_cache[key] = now
            return func(*args, **kwargs)
        return wrapper
    return decorator


def _get_sign(secret: str) -> tuple[str, str]:
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return timestamp, sign


@lock(interval=10)
def send_dd_msg(spider_name: str, msg_name: str, msg_content: str,
                developer: str = None, title: str = "采集引擎告警"):
    """
    发送钉钉告警
    - msg_name 包含 '入库' -> insert_data_token
    - 其他 -> crawl_error_token
    """
    if '入库' in msg_name:
        token = DINGTALK_CONF.get('insert_data_token', '')
    else:
        token = DINGTALK_CONF.get('crawl_error_token', '')

    if not token:
        logger.warning("钉钉 Token 未配置")
        return

    secret = DINGTALK_CONF.get('secret', '')
    url = token
    if secret:
        timestamp, sign = _get_sign(secret)
        url = f"{token}&timestamp={timestamp}&sign={sign}"

    dev_info = f"\n\n> **负责人**: {developer}" if developer else ""
    text = (
        f"## {title}\n\n"
        f"- **爬虫**: `{spider_name}`\n"
        f"- **事件**: {msg_name}\n"
        f"- **详情**: {msg_content}"
        f"{dev_info}\n\n"
        f"> {time.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    try:
        resp = requests.post(url, json={
            "msgtype": "markdown",
            "markdown": {"title": title, "text": text}
        }, timeout=10)
        result = resp.json()
        if result.get('errcode') != 0:
            logger.warning(f"钉钉发送异常: {result}")
        else:
            logger.info(f"钉钉消息已发送: [{spider_name}] {msg_name}")
    except Exception as e:
        logger.error(f"钉钉发送失败: {e}")
