# 引擎架构

> 适用范围：爬虫引擎（crawl_spider_engine）｜最近更新：2026-08-28

## 执行流程

```
scrapy crawl <spider_name> -a start_page=1 -a end_page=3
  → Spider.start_requests()
    → 下载中间件链: UA(500) → Proxy(510) → Cookie(520) → JSL(535) → CurlCFFI(600) → Retry(800)
      → 爬虫中间件: HttpError(543)
        → Pipeline: DedupPipeline(100) → StatsPipeline(200) → MysqlPipeline(310)
          → INSERT IGNORE INTO crawl_data.{table}
```

## Spider 继承链

```
scrapy.Spider
  └── BaseSpider (spiders/base_spider.py)
        ├── 经济类 Spider (直接继承)
        ├── FinanceBaseSpider (金融类，Node.js 签名)
        ├── QyyjtBaseSpider (企业预警通 Token 管理)
        ├── LawBaseSpider (法律类，build_law_item)
        └── NewsBaseSpider (资讯类，LLM 提取)
```

## 目录结构

```
crawl_spider_engine/
├── scrapy.cfg
├── scrapyd.conf             # Scrapyd 服务配置
├── setup.py                 # egg 打包配置
├── settings.py              # Scrapy 全局配置（唯一入口）
├── Dockerfile               # 容器镜像（ENV CURRENT_ENV=prod）
├── entrypoint.sh            # 容器启动：启动 Scrapyd + 打包 egg + auto_deploy 自检测
├── main.py                  # 进程入口
├── config/
│   ├── __init__.py          # 配置加载（Windows → dev.ini / Linux → prod.ini，CURRENT_ENV 可覆盖）
│   ├── dev.ini.example      # 本地配置模板（含 MYSQL/REDIS/KAFKA/LLM/NODE/DINGTALK/MINIO/ADMIN）
│   ├── dev.ini              # 本地开发配置（gitignore，不提交）
│   ├── prod.ini             # 生产配置（gitignore，不提交）
│   ├── spider_registry.json # 爬虫注册表（config_sync 维护）
│   ├── schedule_config.json # 遗留文件（旧 config_sync 导出，2026-06-11 后无代码写入）
├── spiders/
│   ├── base_spider.py       # 爬虫基类
│   ├── economy/             # 经济类：产权/海关/基金/回购/评级/资质/...
│   ├── finance/             # 金融类：债券/IPO/汇率/港股/企业预警通/...
│   ├── law/                 # 法律类：律所/法规/案例/...
│   ├── news/                # 资讯类：LLM 提取
│   └── report/              # 公告类
├── middlewares/
│   ├── ua_middleware.py         # 500 RandomUserAgent
│   ├── proxy_middleware.py      # 510 RandomProxy（按 spider.proxy_type 分发）
│   ├── cookie_middleware.py     # 520 CookieInject
│   ├── waf_middleware.py        # 535 JSL 521 绕过
│   ├── curl_cffi_middleware.py  # 600 TLS 指纹
│   ├── retry_middleware.py      # 800 重试+告警
│   ├── error_middleware.py      # 543 HttpError（爬虫中间件）
│   ├── auth_middleware.py       # 多账号注入/切换/反馈（登录型爬虫自行启用）
│   ├── requests_middleware.py   # requests 兼容
│   ├── universal_fetch_middleware.py
│   └── finance_middlewares/
├── pipelines/
│   ├── dedup_pipeline.py    # 100 库内去重
│   ├── stats_pipeline.py    # 200 计数统计
│   ├── mysql_pipeline.py    # 310 MySQL 入库（INSERT IGNORE）
│   ├── bloom_pipeline.py    # Redis 布隆去重（可选）
│   ├── kafka_pipeline.py    # 320 Kafka（可选）
│   ├── mongodb_pipeline.py  # MongoDB 写入（可选）
│   ├── finance_pipelines/   # 金融类专属（当前仅占位）
│   └── economy_pipelines/   # 经济类专属（当前仅占位）
├── extensions/
│   ├── datedir_log_extension.py  # 50 日志按日期分目录
│   ├── stats_extension.py        # 100 实时统计推 Redis
│   └── heartbeat_extension.py    # 200 心跳上报 Redis
├── utils/
│   ├── mysql_pool.py       # MySQL 连接池
│   ├── redis_client.py     # Redis 连接
│   ├── bloom_filter.py     # 布隆过滤器
│   ├── dingtalk.py         # 钉钉告警
│   ├── proxy_kit.py        # 代理工具（no_proxy/tunnel_proxy/long_proxy）
│   ├── llm_client.py       # LLM 调用
│   ├── node_client.py      # Node.js WAF 签名
│   ├── result_reporter.py  # 运行结果回调
│   ├── time_kit.py         # 时间工具
│   └── text_kit.py         # 文本处理
└── scripts/
    ├── auto_deploy.py      # git push → 自检测（30s）→ egg 热部署
    ├── proxy_checker.py    # 代理可用性检测（5min）
    └── ...                 # 迁移/生成等辅助脚本
```

## 中间件栈

```
下载中间件 (DOWNLOADER_MIDDLEWARES):
  500 RandomUserAgent → 510 RandomProxy → 520 CookieInject
  → 535 JslHandler → 600 CurlCffi → 800 RetryAlarm

爬虫中间件 (SPIDER_MIDDLEWARES):
  543 HttpError

Pipeline (ITEM_PIPELINES):
  100 DedupPipeline → 200 StatsPipeline → 310 MysqlPipeline
  → 320 KafkaPipeline (可选)
```

## 扩展

| 扩展 | 频率 | 说明 |
|------|------|------|
| HeartbeatExtension | 30s | 写 Redis `crawl_engine:heartbeat:{name}` |
| StatsExtension | 5s | 推送 Scrapy stats 到 Redis `yuncrawl_stats:{name}`（历史命名，保留兼容管理平台） |
| DateDirLogExtension | — | 生产环境日志按日期子目录归档 |

## 外部依赖

| 服务 | 用途 | 本地不可用时 |
|------|------|-------------|
| MySQL | 业务数据存储 | Spider 入库失败 |
| Redis | 统计/心跳/去重/账号池 | 降级运行，不影响采集 |
| crawl-proxy-server | 动态代理（PROXY_CONFIG） | 需代理的 Spider 不可用 |
| Node.js 签名服务（内网 10.1.1.19:3000，`NODE_CONF`） | WAF/JS 签名 | 瑞数类网站不可用 |
| LLM Server（内网 10.1.1.19:8000） | AI 新闻提取 | NewsBaseSpider 降级 |
