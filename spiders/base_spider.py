"""
爬虫基类
参数来源优先级：
  1. scrapy crawl -a 传入的 spider args（Scrapyd 调度时注入）
  2. 爬虫类级别的类属性默认值
  3. settings.py 全局默认值
"""
import scrapy
from utils.dingtalk import send_dd_msg

class BaseSpider(scrapy.Spider):

    default_start_page: int = 1
    default_end_page: int = 100
    dedup_fields: list = []
    proxy_type: str = 'no_proxy'  # 默认不走代理（国内网站多数封代理），需要代理的爬虫显式覆盖为 tunnel_proxy

    def __init__(self, start_page=None, end_page=None, jobid=None, **kwargs):
        super().__init__(**kwargs)
        self.start_page = int(start_page) if start_page is not None else self.default_start_page
        self.end_page = int(end_page) if end_page is not None else self.default_end_page
        self.jobid = int(jobid) if jobid is not None else 0
        self.logger.info(f"[{self.name}] 初始化: page={self.start_page}~{self.end_page} jobid={self.jobid}")

    def page_urls(self, template: str) -> list:
        return [template.format(page=p) for p in range(self.start_page, self.end_page + 1)]

    def send_alert(self, msg_name: str, msg_content: str, title: str = "爬虫告警"):
        send_dd_msg(
            spider_name=self.name, msg_name=msg_name, msg_content=msg_content,
            developer=getattr(self, 'developer', ''), title=title)

    def log_info(self, msg: str):
        self.logger.info(f"[{self.name}] {msg}")

    def log_warning(self, msg: str):
        self.logger.warning(f"[{self.name}] {msg}")

    def log_error(self, msg: str):
        self.logger.error(f"[{self.name}] {msg}")
