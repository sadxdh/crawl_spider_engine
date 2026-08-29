"""
企业预警通（qyyjt.cn）爬虫基类

所有 qyyjt 子爬虫继承此类，自动处理：
  - token 获取与注入（Pcuss / User 请求头）
  - 统一分页参数：skip = (page - 1) * PAGE_SIZE
  - 请求失败时的告警
"""
from spiders.base_spider import BaseSpider
from utils.qyyjt_token import ManageToken

_PAGE_SIZE = 50

class QyyjtBaseSpider(BaseSpider):
    """企业预警通爬虫公共基类，子类只需实现 _build_item() 与相关常量。"""

    allowed_domains = ['qyyjt.cn']
    default_end_page = 2   # 增量默认前2页（100条）
    proxy_type = 'no_proxy'  # 登录类爬虫不使用代理

    # 子类必须定义
    _BASE_HEADERS: dict = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._token_mgr = ManageToken()

    # ── token 工具 ──────────────────────────────────────────

    def _get_auth_headers(self, headers) -> dict | None:
        """获取带鉴权信息的 headers，无可用 token 返回 None。"""
        token = self._token_mgr.get_token()
        if not token:
            self.log_warning('暂无可用 token，本次请求跳过')
            return None
        headers = dict(headers)
        headers['Pcuss'] = token['access_token']
        headers['User']  = token['user']
        return headers

    # ── 分页工具 ────────────────────────────────────────────

    @staticmethod
    def page_to_skip(page: int) -> int:
        """将页码（1-based）转换为 skip 偏移量。"""
        return 0 if page == 1 else (page - 1) * _PAGE_SIZE

    # ── 统一错误回调 ────────────────────────────────────────

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
