"""金融类爬虫基类（示例，含Node.js加密支持）"""
import scrapy
from spiders.base_spider import BaseSpider
from utils.node_client import node_client

class FinanceBaseSpider(BaseSpider):
    """
    金融类爬虫基类
    支持 Node.js 调用处理 JS 加密请求（JSL 521、RS 412等）
    """
    def get_js_sign(self, url: str, params: dict = None) -> dict:
        """
        调用 Node.js 服务计算 JS 签名
        用于绕过 JSL 521 等反爬机制
        """
        try:
            result = node_client.exec_js(
                code='return jsl_sign(params.url)',
                params={'url': url, **(params or {})}
            )
            return result.get('data', {})
        except Exception as e:
            self.log_warning(f"JS签名计算失败: {e}")
            return {}

    def get_rs_sign(self, script_name: str, params: dict = None) -> dict:
        """
        调用 Node.js TypeScript 脚本（RS 412 反爬）
        """
        try:
            result = node_client.exec_ts(script_name, params)
            return result.get('data', {})
        except Exception as e:
            self.log_warning(f"RS签名计算失败: {e}")
            return {}

    def build_finance_item(self, **kwargs):
        item = {}
        for k, v in kwargs.items():
            item[k] = v
        return item
