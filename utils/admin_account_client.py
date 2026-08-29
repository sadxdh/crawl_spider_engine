"""
平台凭证客户端 — 通过 Admin API 获取账号/令牌/Cookie
设计原则: 爬虫引擎不直接操作 Redis/MySQL，全部走平台接口
"""
import os
import requests
from loguru import logger

# Docker 容器间通信使用服务名，禁止 localhost
ADMIN_API = os.environ.get('ADMIN_API_URL', 'http://10.88.0.1:5000')
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'dev_token')


class AdminAccountClient:
    """平台凭证客户端 — 单一入口点"""

    @staticmethod
    def _get(url: str, **params) -> dict:
        try:
            r = requests.get(
                f'{ADMIN_API}{url}',
                params=params,
                headers={'Authorization': f'Bearer {ADMIN_TOKEN}'},
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                return data.get('data', {})
        except Exception as e:
            logger.warning(f'[AccountClient] GET {url}: {e}')
        return {}

    @staticmethod
    def acquire(platform: str, spider: str = '') -> dict:
        """获取平台有效凭证（token/cookie自动选择）"""
        params = {'platform': platform}
        if spider:
            params['spider'] = spider
        return AdminAccountClient._get('/api/v1/accounts/acquire', **params)

    @staticmethod
    def get_accounts(platform: str) -> list:
        """获取平台账号列表"""
        result = AdminAccountClient._get('/api/v1/accounts', platform=platform, status='active', page_size=100)
        return result.get('items', result.get('list', []))

    @staticmethod
    def get_token(platform: str) -> dict:
        """获取平台令牌"""
        return AdminAccountClient._get('/api/v1/accounts/acquire', platform=platform)

    @staticmethod
    def get_cookies(platform: str) -> dict:
        """获取平台Cookie（通过 acquire 接口自动获取）"""
        return AdminAccountClient._get('/api/v1/accounts/acquire', platform=platform)


# 全局单例
account_client = AdminAccountClient()
