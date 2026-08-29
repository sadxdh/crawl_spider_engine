"""
账号注入中间件 — 自动管理多账号、替换失效账号、反馈状态到平台

设计原则:
  1. Spider 不关注账号，只发请求
  2. 中间件自动注入 Token/Cookie
  3. 账号失效自动替换 + 重试
  4. 失效状态反馈到 Admin API

Spider 定义失败标志的三种方式:
  方式1: spider.auth_failure_codes = [401, 403, 407]        # HTTP状态码
  方式2: spider.auth_failure_patterns = ['token过期', '登录失效']  # 响应体匹配
  方式3: response.meta['_auth_failure'] = True               # 回调中手动标记
"""
import time, threading, requests as req
from collections import defaultdict
from scrapy import signals
from scrapy.http import HtmlResponse
from loguru import logger

# 平台 → 域名 映射（用于判断哪些请求需要注入账号）
PLATFORM_DOMAINS = {
    'qyyjt': ['qyyjt.cn'],
}

# Admin API 地址（Docker 服务名）
ADMIN_API = 'http://10.88.0.1:5000'
AUTH_TOKEN = 'dev_token'


class AuthMiddleware:
    """多账号自动注入 + 故障切换中间件"""

    def __init__(self):
        self._pools = {}           # platform → [account_dict, ...]
        self._current = {}         # platform → current_account_index
        self._failed = defaultdict(set)  # platform → {failed_phone, ...}
        self._lock = threading.Lock()
        self._last_refresh = {}    # platform → timestamp

    @classmethod
    def from_crawler(cls, crawler):
        mw = cls()
        crawler.signals.connect(mw.spider_opened, signal=signals.spider_opened)
        return mw

    def spider_opened(self, spider):
        pass

    # ══════════════════════════════════════════════════════════
    # 请求前: 注入账号Token/Cookie
    # ══════════════════════════════════════════════════════════

    def process_request(self, request, spider):
        platform = self._get_platform(request.url)
        if not platform:
            return None

        account = self._get_current_account(platform)
        if not account:
            spider.logger.warning(f'[AuthMW] {platform} 无可用账号')
            return None

        token = account.get('access_token')
        if token:
            request.headers['Authorization'] = f'Bearer {token}'
            request.headers['token'] = token

        cookies = account.get('cookie')
        if cookies and isinstance(cookies, dict):
            for k, v in cookies.items():
                if k != 'phone':
                    request.cookies[k] = v

        request.meta['_auth_platform'] = platform
        request.meta['_auth_phone'] = account.get('phone', '')
        return None

    # ══════════════════════════════════════════════════════════
    # 响应后: 检测失效，自动替换
    # ══════════════════════════════════════════════════════════

    def process_response(self, request, response, spider):
        platform = request.meta.get('_auth_platform')
        if not platform:
            return response

        # 方式1: Spider 在回调中设置 meta['_auth_failure'] = True
        if request.meta.get('_auth_failure'):
            return self._handle_failure(request, response, spider, platform, 'spider_callback')

        # 方式2: HTTP 状态码（可被 Spider 覆盖）
        failure_codes = getattr(spider, 'auth_failure_codes', [401, 403])
        if response.status in failure_codes:
            return self._handle_failure(request, response, spider, platform, f'HTTP {response.status}')

        # 方式3: 响应体内容匹配（平台特定错误信息）
        failure_patterns = getattr(spider, 'auth_failure_patterns', [])
        if failure_patterns:
            body = response.text[:2000] if hasattr(response, 'text') else ''
            for pattern in failure_patterns:
                if pattern in body:
                    return self._handle_failure(request, response, spider, platform, f'pattern:{pattern}')

        return response

    def _handle_failure(self, request, response, spider, platform, reason):
        """统一处理账号失效"""
        phone = request.meta.get('_auth_phone', '')
        if not phone:
            return response

        self._mark_failed(platform, phone)
        self._report_failure(platform, phone, response.status if hasattr(response, 'status') else 0)
        spider.logger.warning(f'[AuthMW] {platform}/{phone} 失效({reason}), 切换账号')

        new_account = self._switch_account(platform)
        if new_account:
            return self._retry_with_account(request, new_account, spider)
        spider.logger.error(f'[AuthMW] {platform} 所有账号已失效')
        return response

    # ══════════════════════════════════════════════════════════
    # 账号池管理
    # ══════════════════════════════════════════════════════════

    def _get_platform(self, url: str) -> str:
        """根据URL判断属于哪个平台"""
        for platform, domains in PLATFORM_DOMAINS.items():
            for d in domains:
                if d in url:
                    return platform
        return ''

    def _get_current_account(self, platform: str) -> dict:
        """获取当前可用账号"""
        with self._lock:
            self._refresh_if_needed(platform)
            pool = self._pools.get(platform, [])
            if not pool:
                return {}
            idx = self._current.get(platform, 0)
            # 跳过已失效的
            for _ in range(len(pool)):
                account = pool[idx % len(pool)]
                phone = account.get('phone', '')
                if phone not in self._failed.get(platform, set()):
                    self._current[platform] = idx % len(pool)
                    return account
                idx += 1
            return {}

    def _switch_account(self, platform: str) -> dict:
        """切换到下一个账号"""
        with self._lock:
            pool = self._pools.get(platform, [])
            if not pool:
                return {}
            current = self._current.get(platform, 0)
            self._current[platform] = (current + 1) % len(pool)
            return pool[self._current[platform]]

    def _mark_failed(self, platform: str, phone: str):
        """标记账号失效"""
        with self._lock:
            self._failed[platform].add(phone)

    def _refresh_if_needed(self, platform: str):
        """从平台API刷新账号池（每5分钟）"""
        now = time.time()
        if now - self._last_refresh.get(platform, 0) < 300:
            return
        self._last_refresh[platform] = now
        try:
            resp = req.get(
                f'{ADMIN_API}/api/v1/accounts/acquire',
                params={'platform': platform, 'all': '1'},
                headers={'Authorization': f'Bearer {AUTH_TOKEN}'},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json().get('data', {})
                accounts = data.get('accounts', [data])  # 单个或列表
                with self._lock:
                    valid = [a for a in accounts if a.get('phone', '') not in self._failed.get(platform, set())]
                    self._pools[platform] = valid or accounts  # 全失效时保留原始列表
                    self._current[platform] = 0
                    logger.info(f'[AuthMW] {platform} 账号池刷新: {len(valid)}/{len(accounts)} 可用')
        except Exception as e:
            logger.warning(f'[AuthMW] 刷新账号池失败: {e}')

    # ══════════════════════════════════════════════════════════
    # 失效反馈
    # ══════════════════════════════════════════════════════════

    def _report_failure(self, platform: str, phone: str, status: int):
        """向 Admin API 报告账号失效"""
        try:
            req.post(
                f'{ADMIN_API}/api/v1/accounts/report',
                json={
                    'platform': platform, 'phone': phone,
                    'status': 'failure', 'http_status': status,
                    'reason': f'HTTP {status}',
                },
                headers={'Authorization': f'Bearer {AUTH_TOKEN}'},
                timeout=5,
            )
            logger.info(f'[AuthMW] 已报告账号失效: {platform}/{phone}')
        except Exception as e:
            logger.warning(f'[AuthMW] 报告失效失败: {e}')

    # ══════════════════════════════════════════════════════════
    # 重试
    # ══════════════════════════════════════════════════════════

    def _retry_with_account(self, request, account, spider):
        """用新账号重建请求"""
        new_req = request.replace()
        token = account.get('access_token')
        if token:
            new_req.headers['Authorization'] = f'Bearer {token}'
        new_req.meta['_auth_platform'] = request.meta['_auth_platform']
        new_req.meta['_auth_phone'] = account.get('phone', '')
        new_req.dont_filter = True
        return new_req
