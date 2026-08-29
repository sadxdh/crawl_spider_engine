"""流式采集器包（v6.3 §3.3 双模式采集 · 流模式）

与 Scrapy 批处理爬虫（spiders/）并列，承载秒级高频采集：
  - flash_news_collector  财经快讯流（T1 新闻收编：新浪/见闻/Finnhub/BlockBeats/TreeOfAlpha）
  - tg_collector          TG 频道流（C2，待建）
  - market_collector      交易所行情/微观流（C3/C5，T2，待建）
  - onchain_collector     链上事件流（C4，T3，待建）

统一约定（v6.2）：
  - 所有采集数据最终落 MySQL crawl_data（唯一数据底座），Redis 仅传输/心跳/统计
  - 心跳 Redis `crawl_engine:heartbeat:{name}`（TTL 120s），统计 `yuncrawl_stats:{name}`，与管理平台兼容
  - 调度以数据库为准（admin_server 持久化）；本目录进程为执行单元
"""
