# crawl_spider_engine

爬虫采集引擎：Scrapy + Scrapyd，140 个结构化爬虫覆盖 **经济 / 金融 / 法律 / 资讯 / 公告** 五大类，统一继承 `BaseSpider`，经管道链去重/统计后入库 `crawl_data`。

## 技术栈与端口

| 项 | 值 |
|----|----|
| 技术栈 | Scrapy + Scrapyd（Python），MySQL 入库 + Redis 心跳/统计 |
| 端口 | 6800（Scrapyd API / Web） |

## 爬虫分类体系

```
spiders/
├── economy/    # 经济类：产权/海关/基金/回购/评级/资质/软件违规/物料/土地/专利/...
├── finance/    # 金融类：债券/IPO/汇率/港股/企业预警通/上市公司（东方财富）/...
├── law/        # 法律类：律所/法规/案例/...
├── news/       # 资讯类：LLM 提取
└── report/     # 公告类：公司公告/债券公告/新三板公告/税务公告/...
（另有 company / monitor / other 等辅助分类子目录）
```

### BaseSpider 继承链

```
scrapy.Spider
  └── BaseSpider (spiders/base_spider.py)
        ├── 经济类 Spider (直接继承)
        ├── FinanceBaseSpider (finance/finance_base_spider.py)
        ├── QyyjtBaseSpider (finance/qyyjt/qyyjt_base_spider.py，企业预警通 Token 管理)
        ├── LawBaseSpider (law/law_base_spider.py)
        └── NewsBaseSpider (news/news_base_spider.py)
```

### 管道与中间件

```
管道链: DedupPipeline (100) → StatsPipeline (200) → MysqlPipeline (310)
                                                 → KafkaPipeline (320, 可选)
下载中间件: RandomUserAgent (500) → RandomProxy (510) → CookieInject (520) → RetryAlarm (800)
爬虫中间件: HttpError (543)
扩展: Stats (100) → Heartbeat (200) → DateDirLog (50)
```

## 双模式采集（v6.3：批模式 + 流模式）

引擎现支持两种采集模式，统一注册进 crawl_admin_server 监控：

```
spiders/      [批模式] Scrapy 爬虫（140+，定时调度，INSERT IGNORE 入库）
collectors/   [流模式] 流式采集器（独立进程，非 Scrapy，秒级轮询/事件驱动）
```

### 流式采集器（collectors/）

| 采集器 | 数据 | 表 | 轮询 | 来源 |
|--------|------|-----|:--:|------|
| flash_news | 财经快讯（新浪/见闻/Finnhub/BlockBeats/TreeOfAlpha） | flash_news | 5s | 情报部 news_fetcher 迁入 |
| tg_news | TG 频道快讯（Telethon，需配置） | flash_news | 事件 | 情报部 news_tg 迁入 |
| market_quote | OKX 行情（ticker/candle/funding/oi/mark_price/order_book） | market_data | 60s | 交易部行情迁入 |
| onchain_quote | Binance 行情 + Etherscan 链上健康 | onchain_data | 120s | 风控部迁入 |
| macro_market | Sina 宏观行情（A股/美股/黄金/原油/外汇/加密） | macro_market | 300s | 情报部日报迁入 |
| sentiment_metrics | Fear&Greed + CoinGecko 市值/板块 | sentiment_metrics | 600s | 情报部辅助指标迁入 |
| gate_micro | Gate 合约微观（tickers/order_book/funding_rate） | gate_micro | 60s | 情报部 market_maker 迁入 |

**运行**（独立进程，由 collector_supervisor 管理）：

```bash
# 单个运行
python -m collectors.flash_news_collector
# 全部管理：crawl_admin_server 的 collector_supervisor（DB 期望态驱动）
python -m app.jobs.collector_supervisor
```

**约定（v6.3）**：所有采集数据最终落 MySQL `crawl_data`（唯一数据底座），
Redis 仅心跳/统计/控制（`crawl_engine:heartbeat:*` / `yuncrawl_stats:*` / `crawl_admin:collector:cmd`）；
流式采集器注册进 `collector_registry`（admin 统一调度/监控），DB 持久化期望态，进程重启按库恢复。

## 快速开始

### 本地调试爬虫

```bash
cd crawl_spider_engine
.venv/Scripts/python.exe -m scrapy crawl <spider_name> -a start_page=1 -a end_page=3
```

> 增量运行参数 `-a start_page` / `-a end_page` 由 `BaseSpider` 解析；`spider_name` / `crawl_time` 由管道自动注入，Spider 无需处理。

### 启动 Scrapyd

```bash
cd crawl_spider_engine
scrapyd
# → http://localhost:6800
```

### 部署（Docker + Scrapyd）

```bash
cd crawl_spider_engine
docker build -t crawl_spider_engine:latest .
```

- 随平台一键部署：`crawl_admin_server/docker/docker-compose.yml` 中的 `scrapyd` 服务（:6800）即构建本镜像
- 代码更新：`git push` → `scripts/auto_deploy.py` 自动检测 → Scrapyd egg 热部署（不中断运行中 Job）

## 目录结构

```
crawl_spider_engine/
├── spiders/            # 爬虫（按五类分目录，base_spider.py 提供公共能力）
├── pipelines/          # 管道（dedup / stats / mysql / kafka / bloom / mongodb）
├── middlewares/        # 中间件（UA / 代理 / Cookie / 重试告警 / WAF / curl_cffi / ...）
├── extensions/         # 扩展（stats / heartbeat / datedir_log）
├── scripts/            # 运维脚本（auto_deploy / proxy_checker / migrate_to_prod / ...）
├── settings.py         # Scrapy 配置（SPIDER_MODULES / ITEM_PIPELINES / 中间件顺序）
├── scrapy.cfg          # Scrapy 项目配置
├── scrapyd.conf        # Scrapyd 服务配置
├── setup.py            # Scrapyd egg 打包
├── main.py / entrypoint.sh
└── Dockerfile
```

> 说明：本引擎不使用 Scrapy Item 类，Spider 直接 `yield dict`；`spiders/` 各子目录自带 README 记录爬虫清单与数据表（如 `spiders/finance/listed_company_eastmoney/README.md`）。

## 文档

- 爬虫开发：[docs/SPIDER_DEV.md](docs/SPIDER_DEV.md) ｜ 架构：[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) ｜ API：[docs/API.md](docs/API.md)
- 运维：[docs/OPS.md](docs/OPS.md) ｜ 配置：[docs/CONFIG.md](docs/CONFIG.md) ｜ 部署：[docs/DEPLOY.md](docs/DEPLOY.md)
- 平台手册：[docs/](../docs/) ｜ 爬虫迁移命令：[migrate-spider](../.claude/commands/migrate-spider.md)
