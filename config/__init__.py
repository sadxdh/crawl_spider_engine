"""
配置加载器 - 参考 data_crawl_server/crawl/config/config.py
自动检测运行环境（Windows=dev, Linux=prod），支持 CURRENT_ENV 环境变量覆盖
"""
import os
import platform
import configparser

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV = os.environ.get('CURRENT_ENV', 'dev' if platform.system() == 'Windows' else 'prod')
_CONFIG_FILE = os.path.join(_BASE_DIR, f'{_ENV}.ini')

# 为缺失的环境变量提供占位默认值，避免 configparser 插值报错
_env_defaults = {
    # 数据库
    'SPIDER_MYSQL_HOST_PROD': 'py.w.com',
    'SPIDER_MYSQL_USER_PROD': 'root',
    'SPIDER_MYSQL_PASSWORD_PROD': 'IK29lKb0',
    # Redis
    'SPIDER_REDIS_HOST_PROD': 'py.w.com',
    'SPIDER_REDIS_PASSWORD_PROD': 'R09.jos6pl',
    'SPIDER_REDIS_USER_PROD': '',
    # Kafka
    'SPIDER_KAFKA_HOST_PROD': 'py.w.com:9092',
    # 节点服务
    'SPIDER_NODE_SERVER_PROD': '10.1.1.19:3000',
    # 代理（与旧项目一致）
    'SPIDER_PROXY_SERVER_PROD': '1wnv4qzl7pfzlk04xoo7.manage.wintaocloud.com',
    'SPIDER_PROXY_USERNAME_PROD': '',
    'SPIDER_PROXY_PASSWORD_PROD': '',
    # LLM
    'SPIDER_LLM_HOST_PROD': '10.1.1.19:8000',
    'SPIDER_LLM_API_KEY_PROD': 'lm-studio',
    # OSS/MinIO
    'SPIDER_OSS_SERVER_PROD': 'ossn.wintaocloud.com',
    'SPIDER_OSS_ENDPOINT_PROD': 'ossn.wintaocloud.com',
    'SPIDER_OSS_KEY_ID_PROD': '',
    'SPIDER_OSS_KEY_SECRET_PROD': '',
    'SPIDER_OSS_BUCKET_NAME_PROD': 'pdffile',
    'SPIDER_MINIO_ACCESS_DEV': '',
    'SPIDER_MINIO_SECRET_DEV': '',
    'SPIDER_MINIO_ACCESS_PROD': '',
    'SPIDER_MINIO_SECRET_PROD': '',
    # 其他
}
for _k, _v in _env_defaults.items():
    os.environ.setdefault(_k, _v)

_parser = configparser.ConfigParser(os.environ)
_parser.read(_CONFIG_FILE, encoding='utf-8')


def _get(section: str, key: str, fallback: str = '') -> str:
    return _parser.get(section, key, fallback=fallback)


# ─── MySQL ────────────────────────────────────────────────
DB_CONF = {
    'host':     _get('MYSQL', 'host', 'localhost'),
    'user':     _get('MYSQL', 'user', 'root'),
    'password': _get('MYSQL', 'password', ''),
    'charset':  'utf8mb4',
    'port':     int(_get('MYSQL', 'port', '3306')),
    'database': _get('MYSQL', 'dbname', 'crawl_data'),
}

# ─── Redis ────────────────────────────────────────────────
REDIS_CONF = {
    'host':     _get('REDIS', 'host', 'localhost'),
    'port':     int(_get('REDIS', 'port', '6379')),
    'password': _get('REDIS', 'password', '') or None,
    'db':       int(_get('REDIS', 'db', '1')),
}

# ─── Kafka ────────────────────────────────────────────────
KAFKA_CONF = {
    'host':  _get('KAFKA', 'host', 'localhost:9092'),
    'topic': _get('KAFKA', 'topic', 'crawl_data'),
}

# ─── LLM ─────────────────────────────────────────────────
LLM_CONF = {
    'host':    _get('LLM', 'host', ''),
    'api_key': _get('LLM', 'api_key', 'lm-studio'),
    'model':   _get('LLM', 'model', 'Qwen/Qwen3-1.7B'),
}

# ─── Node.js 服务 ─────────────────────────────────────────
NODE_CONF = {
    'exec_js_url': _get('NODE', 'exec_js_url', ''),
    'exec_ts_url': _get('NODE', 'exec_ts_url', ''),
    'exec_ck_url': _get('NODE', 'exec_ck_url', ''),
}

# ─── 钉钉 ────────────────────────────────────────────────
DINGTALK_CONF = {
    'crawl_error_token': _get('DINGTALK', 'crawl_error_token', ''),
    'insert_data_token': _get('DINGTALK', 'insert_data_token', ''),
    'secret':            _get('DINGTALK', 'secret', ''),
}

# ─── 管理平台 API ─────────────────────────────────────────
ADMIN_CONF = {
    'api_url':   _get('ADMIN', 'api_url', 'http://10.88.0.1:5000'),
    'api_token': _get('ADMIN', 'api_token', ''),
}

# ─── MinIO / OSS ──────────────────────────────────────────
MINIO_CONF = {
    'endpoint':    _get('MINIO', 'endpoint', 'ossn.wintaocloud.com'),
    'access_key':  _get('MINIO', 'access_key', ''),
    'secret_key':  _get('MINIO', 'secret_key', ''),
    'secure':      _parser.getboolean('MINIO', 'secure', fallback=False),
    'region':      _get('MINIO', 'region', 'cn-wdy-1'),
    'bucket_name': _get('MINIO', 'bucket_name', 'pdffile'),
}

# ─── Redis Key 命名空间 ───────────────────────────────────
ENGINE_PREFIX   = 'crawl_engine:'
DUPEFILTER_KEY  = 'crawl_engine:dupefilter:req:{}'  # 布隆过滤器（per-spider）
STATS_KEY       = 'yuncrawl_stats:{}'               # 运行时统计（与 crawl_admin_server 兼容）
HEARTBEAT_KEY   = 'crawl_engine:heartbeat:{}'       # 心跳（TTL=120s）

# ─── 代理配置 ─────────────────────────────────────────────
def _proxy_base():
    host = os.environ.get('SPIDER_PROXY_SERVER_PROD', '1wnv4qzl7pfzlk04xoo7.manage.wintaocloud.com')
    return f'http://{host}/crawl-proxy-server/manage_proxy'

PROXY_CONFIG = {
    'tunnel_proxy_url': f'{_proxy_base()}/get_dynamic_proxy',
    'static_proxy_url': f'{_proxy_base()}/get_static_proxy',
    'username': os.environ.get('SPIDER_PROXY_USERNAME_PROD', ''),
    'password': os.environ.get('SPIDER_PROXY_PASSWORD_PROD', ''),
}

# ─── Scrapyd 配置 ─────────────────────────────────────────
SCRAPYD_URL = os.environ.get('SCRAPYD_URL', 'http://localhost:6800')

# ─── 账号/Cookie池 Key（与现有服务兼容）─────────────────
ACCOUNT_POOL_REDIS_KEY = '{}:account_pool'
COOKIES_POOL_REDIS_KEY = '{}:cookie_pool'
ACCOUNT_INFO_REDIS_KEY = '{}:account_info'

CURRENT_ENV = _ENV
