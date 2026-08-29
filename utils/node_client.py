"""
Node.js 服务客户端 - 用于执行 JS 加密/解密
支持 JSL 521、RS 412 等反爬逻辑绕过
"""
import requests
from loguru import logger
from config import NODE_CONF


class NodeClient:
    """Node.js 服务调用客户端（单例）"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def exec_js(self, code: str, params: dict = None, timeout: int = 10) -> dict:
        """执行 JS 代码"""
        url = NODE_CONF.get('exec_js_url', '')
        if not url:
            raise ValueError("NODE exec_js_url 未配置")
        try:
            resp = requests.post(url, json={'code': code, 'params': params or {}}, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"[NodeClient] exec_js 失败: {e}")
            raise

    def exec_ts(self, script_name: str, params: dict = None, timeout: int = 10) -> dict:
        """执行 TypeScript 脚本（RS 412 反爬）"""
        url = NODE_CONF.get('exec_ts_url', '')
        if not url:
            raise ValueError("NODE exec_ts_url 未配置")
        try:
            resp = requests.post(url, json={'script': script_name, 'params': params or {}}, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"[NodeClient] exec_ts 失败: {e}")
            raise

    def get_cookie(self, platform: str, params: dict = None, timeout: int = 30) -> dict:
        """获取平台 Cookie（Node 自动登录）"""
        url = NODE_CONF.get('exec_ck_url', '')
        if not url:
            raise ValueError("NODE exec_ck_url 未配置")
        try:
            resp = requests.post(url, json={'platform': platform, 'params': params or {}}, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"[NodeClient] get_cookie 失败: {e}")
            raise


node_client = NodeClient()
