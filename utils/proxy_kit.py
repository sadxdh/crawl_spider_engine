"""
代理工具
兼容两种响应格式：
  旧: {"proxy": "http://1.2.3.4:5678"}
  新: {"status":"success","proxy":{"http":"http://...","https":"http://..."}}
"""
import requests
from loguru import logger
from config import PROXY_CONFIG


def _extract_proxy(result: dict) -> str | None:
    """从 API 响应中提取代理地址，兼容新旧格式"""
    proxy = result.get('proxy') or result.get('data', {}).get('proxy')
    if not proxy:
        return None
    if isinstance(proxy, dict):
        # 新格式: {"http": "...", "https": "..."}
        return proxy.get('http') or proxy.get('https')
    if isinstance(proxy, str):
        return proxy if proxy.startswith('http') else f'http://{proxy}'
    return None


class ScrapyProxy:

    @classmethod
    def return_proxy(cls, proxy_type: str) -> str | None:
        if proxy_type == 'no_proxy' or not proxy_type:
            return None
        elif proxy_type == 'tunnel_proxy':
            return cls.get_tunnel_proxy()
        elif proxy_type == 'long_proxy':
            return cls.get_long_proxy()
        elif proxy_type == 'local_proxy':
            return None
        else:
            logger.warning(f"未知代理类型: {proxy_type}")
            return None

    @classmethod
    def get_long_proxy(cls) -> str | None:
        """获取长效代理"""
        return cls._fetch(PROXY_CONFIG.get('static_proxy_url', ''))

    @classmethod
    def get_tunnel_proxy(cls) -> str | None:
        """获取隧道代理"""
        return cls._fetch(PROXY_CONFIG.get('tunnel_proxy_url', ''))

    @classmethod
    def _fetch(cls, url: str) -> str | None:
        if not url:
            return None
        try:
            resp = requests.get(url, timeout=5)
            return _extract_proxy(resp.json())
        except Exception as e:
            logger.warning(f'[ProxyKit] 获取代理失败 {url}: {e}')
            return None
