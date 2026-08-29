"""
Scrapy 基础配置
架构：纯 Scrapy 项目，由 Scrapyd 管理进程
爬虫通过 scrapy crawl <name> -a key=val 接收参数
"""
import sys
import os
import logging
import platform

# 确保项目根目录在 sys.path
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── loguru → Python logging 桥接 ─────────────────────────
# Scrapyd 把 Scrapy 日志写入 LOG_FILE，loguru 默认走 stderr 不进文件。
# 这里把 loguru 的输出转发给 Python logging，统一由 Scrapy 管理。
from loguru import logger as _loguru_logger

class _PropagateHandler(logging.Handler):
    """把 loguru 记录转发给 Python logging"""
    def emit(self, record):
        logging.getLogger(record.name).handle(record)

_loguru_logger.remove()   # 移除默认 stderr sink
_loguru_logger.add(
    _PropagateHandler(),
    format="{message}",
    level="DEBUG",
)

# ── 项目标识 ──────────────────────────────────────────────
BOT_NAME = 'crawl_spider_engine'
SPIDER_MODULES = ['spiders']
NEWSPIDER_MODULE = 'spiders'

# ── 并发控制（默认值，可被爬虫 custom_settings 覆盖）────────
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8
DOWNLOAD_DELAY = 0.5
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_TIMEOUT = 20
AUTOTHROTTLE_ENABLED = False   # 由各爬虫自己决定是否开启

# ── 重试 ──────────────────────────────────────────────────
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# ── 中间件（全局启用，各爬虫可用 custom_settings 禁用）────────
DOWNLOADER_MIDDLEWARES = {
    # 关闭 Scrapy 默认 UA
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    # 随机 UA
    'middlewares.ua_middleware.RandomUserAgentMiddleware': 500,
    # 动态代理（根据 spider.proxy_type 决定是否使用）
    'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
    # Cookie 注入（根据 spider.use_cookie 决定是否注入）
    'middlewares.cookie_middleware.CookieInjectMiddleware': 520,
    # TLS 指纹绕过（curl_cffi，仅对配置的域名生效）
    'middlewares.curl_cffi_middleware.CurlCffiMiddleware': 600,
    # 加速乐 JSL 521 绕过
    'middlewares.waf_middleware.JslHandlerMiddleware': 535,
    # AuthMiddleware: 多账号注入+切换+反馈 — 由需要登录的爬虫自行启用
    # 重试 + 超阈值钉钉告警
    'middlewares.retry_middleware.RetryAlarmMiddleware': 800,
    # 关闭默认重试（由 RetryAlarmMiddleware 接管）
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
}

SPIDER_MIDDLEWARES = {
    'middlewares.error_middleware.HttpErrorMiddleware': 543,
}

# ── Pipeline（默认：SQL去重 → 统计 → MySQL）─────────────────
# 各爬虫可通过 custom_settings 替换 Pipeline
# 如需布隆过滤器去重（依赖 Redis），替换为 pipelines.bloom_pipeline.BloomFilterPipeline
ITEM_PIPELINES = {
    'pipelines.dedup_pipeline.DedupPipeline': 100,
    'pipelines.stats_pipeline.StatsPipeline': 200,
    'pipelines.mysql_pipeline.MysqlPipeline': 310,
}

# ── 扩展 ──────────────────────────────────────────────────
EXTENSIONS = {
    'scrapy.extensions.logstats.LogStats': None,              # 禁用默认 LogStats
    'extensions.stats_extension.StatsExtension': 100, # 每5s推送stats到Redis
    'extensions.heartbeat_extension.HeartbeatExtension': 200,  # 心跳
    # 生产环境：将日志重定向到日期子目录 logs/{project}/{spider}/{YYYY-MM-DD}/{hash}.log
    'extensions.datedir_log_extension.DateDirLogExtension': 50,
}

# ── 去重（使用内置指纹去重，布隆过滤在 Pipeline 层处理）──────
DUPEFILTER_CLASS = 'scrapy.dupefilters.RFPDupeFilter'

# ── 日志 ──────────────────────────────────────────────────
LOG_ENABLED = True
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
LOG_DATEFORMAT = '%Y-%m-%d %H:%M:%S'
# Scrapyd 调度时自动将日志写入 logs/{project}/{spider}/{job_id}.log，
# 无需在 settings 中指定 LOG_FILE。本地开发日志只输出到控制台。

# ── 其他 ──────────────────────────────────────────────────
ROBOTSTXT_OBEY = False
TELNETCONSOLE_ENABLED = False
COOKIES_ENABLED = False          # 统一由 CookieInjectMiddleware 管理
REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'

# ── 爬虫参数默认值（BaseSpider 读取这些兜底值）──────────────
DEFAULT_START_PAGE = 1
DEFAULT_END_PAGE = 100
DEFAULT_PROXY_TYPE = 'no_proxy'
DEFAULT_CONCURRENT_REQUESTS = 16
DEFAULT_DOWNLOAD_DELAY = 0.5
