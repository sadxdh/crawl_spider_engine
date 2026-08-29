"""
爬虫执行结果上报到 crawl_admin_server
通过 HTTP API 回写运行状态
"""
import requests
from loguru import logger
from config import ADMIN_CONF


class ResultReporter:
    """将爬虫执行结果上报到管理平台"""

    def __init__(self):
        self.api_url = ADMIN_CONF.get('api_url', '')
        self.api_token = ADMIN_CONF.get('api_token', '')
        self._enabled = bool(self.api_url)

    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
        }

    def report_start(self, spider_name: str, run_id: str):
        """报告爬虫开始运行"""
        if not self._enabled:
            return
        try:
            requests.post(
                f"{self.api_url}/api/v1/monitor/run-logs",
                json={'spider_name': spider_name, 'run_id': run_id, 'status': 'running'},
                headers=self._headers(),
                timeout=5,
            )
        except Exception as e:
            logger.debug(f"[Reporter] 上报开始失败（可忽略）: {e}")

    def report_finish(self, spider_name: str, run_id: str,
                      status: str, items_count: int = 0, error_msg: str = None):
        """报告爬虫完成"""
        if not self._enabled:
            return
        try:
            requests.patch(
                f"{self.api_url}/api/v1/monitor/run-logs/{run_id}",
                json={
                    'status': status,
                    'items_count': items_count,
                    'error_msg': error_msg,
                },
                headers=self._headers(),
                timeout=5,
            )
        except Exception as e:
            logger.debug(f"[Reporter] 上报完成失败（可忽略）: {e}")


result_reporter = ResultReporter()
