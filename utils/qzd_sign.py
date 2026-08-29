"""
企知道 (qizhidao.com) 签名生成工具
移植自 data_crawl_server/crawl/utils/decrypt.py → decrypt_sign_qzd_spider
JS文件来自旧项目 static/qzd_sign.js
"""
import os
from py_mini_racer import MiniRacer


# 一次性加载并编译 JS
_js_code = None
_executor = None


def _get_executor():
    global _js_code, _executor
    if _executor is not None:
        return _executor
    js_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'qzd_sign.js')
    if not os.path.exists(js_path):
        js_path = os.path.join(os.path.dirname(__file__), 'static', 'qzd_sign.js')
    if not os.path.exists(js_path):
        raise FileNotFoundError(f'qzd_sign.js not found at {js_path}')
    with open(js_path, 'r', encoding='utf-8') as f:
        _js_code = f.read()
    _executor = MiniRacer()
    _executor.eval(_js_code)
    return _executor


def get_signature(token: str, call_func: str = 'get_signature_39') -> str:
    """生成企知道 API 签名"""
    executor = _get_executor()
    return executor.call(call_func, token)
