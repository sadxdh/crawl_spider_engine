# 配置说明

> 适用范围：爬虫引擎（crawl_spider_engine）｜最近更新：2026-08-28

## 配置加载

`config/__init__.py` 自动检测环境选择配置文件，`CURRENT_ENV` 环境变量可覆盖：

```
Windows → dev.ini   （默认）
Linux   → prod.ini  （默认，Dockerfile 内置 CURRENT_ENV=prod）
CURRENT_ENV=dev|prod  → 显式指定
```

- **本地开发均使用 `dev.ini`**，无需设置环境变量
- `docker.ini` 已废弃删除；`CURRENT_ENV` 只取 `dev` / `prod`

## dev.ini 配置

首次使用需从模板创建（模板不含真实凭据）：

```bash
cp config/dev.ini.example config/dev.ini
# 编辑 dev.ini 填写本地连接信息
```

`dev.ini` / `prod.ini` 已加入 `.gitignore`，本地修改不会上传，**禁止提交生产密码**。

```ini
[MYSQL]
host = py.w.com
user = root
password = <开发库密码>
port = 3306
dbname = crawl_data

[REDIS]
host = py.w.com
password = <本地密码>
port = 6379
db = 3

# 以下按需配置，大部分爬虫不需要
[KAFKA]
host = py.w.com:9092
topic = monitor_news

[LLM]
host = http://10.1.1.19:8000/v1/chat/completions
api_key = lm-studio
model = Qwen/Qwen3-1.7B

[NODE]
exec_js_url = http://10.1.1.19:3000/exec_jsc
exec_ts_url = http://10.1.1.19:3000/rs_ts
exec_ck_url = http://10.1.1.19:3000/rs_cookie

[DINGTALK]
crawl_error_token = <钉钉机器人地址>
insert_data_token = <钉钉机器人地址>
secret = <签名密钥>

[MINIO]
endpoint = ossn.wintaocloud.com
access_key = <AK>
secret_key = <SK>
secure = false
region = cn-wdy-1
bucket_name = pdffile

[ADMIN]
api_url = http://backend:5000
api_token = <管理平台 Token>
```

> 代理不写在 ini：`PROXY_CONFIG` 由环境变量驱动（`SPIDER_PROXY_SERVER_PROD` 等，见 `config/__init__.py` 占位默认值）。

## 导出的配置字典

`config/__init__.py` 解析后导出以下字典，各模块直接 import 使用：

| 字典 | 使用模块 |
|------|----------|
| `DB_CONF` | `utils/mysql_pool.py`、`pipelines/mysql_pipeline.py` |
| `REDIS_CONF` | `utils/redis_client.py`、`extensions/` |
| `KAFKA_CONF` | `pipelines/kafka_pipeline.py` |
| `LLM_CONF` | `utils/llm_client.py` |
| `NODE_CONF` | `utils/node_client.py` |
| `DINGTALK_CONF` | `utils/dingtalk.py` |
| `ADMIN_CONF` | `utils/result_reporter.py`（运行结果回调） |
| `MINIO_CONF` | OSS/MinIO 文件存储 |
| `PROXY_CONFIG` | `middlewares/proxy_middleware.py`、`utils/proxy_kit.py`（env 驱动） |
| `SCRAPYD_URL` | 热部署/调度 |

## settings.py 关键默认值

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `CONCURRENT_REQUESTS` | 16 | 全局并发数 |
| `DOWNLOAD_DELAY` | 0.5 | 下载延迟（秒） |
| `DOWNLOAD_TIMEOUT` | 20 | 下载超时（秒） |
| `RETRY_TIMES` | 3 | 最大重试次数 |
| `COOKIES_ENABLED` | False | 默认禁用 Cookie（由 CookieInject 管理） |
| `LOG_LEVEL` | INFO | 日志级别 |

## Redis Key 模板

| Key | TTL | 说明 |
|-----|-----|------|
| `crawl_engine:dupefilter:req:{spider_name}` | — | 布隆过滤器（per-spider） |
| `crawl_engine:heartbeat:{spider_name}` | 120s | 心跳 |
| `yuncrawl_stats:{spider_name}` | 3600s | 爬虫实时统计（历史命名，保留兼容 crawl_admin_server 监控） |

## 账号/Cookie 池 Key（与现有服务兼容）

| Key 模板 | 说明 |
|----------|------|
| `{platform}:account_pool` | 账号池 |
| `{platform}:cookie_pool` | Cookie 池 |
| `{platform}:account_info` | 账号信息 |
