# 参数 & 基类 API 参考

> 适用范围：爬虫引擎（crawl_spider_engine）｜最近更新：2026-08-28

## Spider 运行参数

通过 `scrapy crawl` 的 `-a` 传入，由 `BaseSpider.__init__` 接收并自动类型转换。

### 核心参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `start_page` | int | 1 | 起始页 |
| `end_page` | int | 100 | 结束页 |
| `proxy_type` | str | `no_proxy` | `no_proxy` / `tunnel_proxy` / `long_proxy` |
| `use_cookie` | int | 0 | 是否注入 Cookie |
| `cookie_platform` | str | spider.name | Cookie 池平台标识 |
| `cookie_pool_type` | str | `hash` | `hash`（HRANDFIELD）/ `list`（LMOVE） |
| `bloom_reset` | bool | False | 是否重置布隆过滤器 |
| `data_table` | str | spider.name | 目标数据表名 |
| `create_table_rule` | str | `common` | `common` / `custom` |
| `developer` | str | '' | 负责人（钉钉告警用） |
| `download_delay` | float | 0.5 | 覆盖全局下载延迟 |
| `concurrent_requests` | int | 16 | 覆盖全局并发数 |

### 使用示例

```bash
# 基本用法
.venv/Scripts/python.exe -m scrapy crawl economy_my_spider -a start_page=1 -a end_page=3

# 指定代理
.venv/Scripts/python.exe -m scrapy crawl economy_my_spider -a start_page=1 -a end_page=1 -a proxy_type=tunnel_proxy

# DEBUG 日志
.venv/Scripts/python.exe -m scrapy crawl economy_my_spider -a start_page=1 -a end_page=1 -s LOG_LEVEL=DEBUG
```

---

## BaseSpider 属性

| 属性 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `name` | str | — | 唯一标识 `{category}_{name}` |
| `data_table` | str | — | 写入的 MySQL 表名 |
| `dedup_fields` | list | [] | 去重字段列表 |
| `allowed_domains` | list | — | 允许的域名 |
| `proxy_type` | str | `no_proxy` | 代理类型 |
| `default_start_page` | int | 1 | 默认起始页 |
| `default_end_page` | int | 100 | 默认结束页 |
| `custom_settings` | dict | — | 覆盖 settings.py |

## BaseSpider 方法

| 方法 | 说明 |
|------|------|
| `self.page_urls(template)` | 分页 URL 生成 `template.format(page=N)`，返回 list |
| `self.log_info(msg)` | INFO 日志 |
| `self.log_warning(msg)` | WARNING 日志 |
| `self.log_error(msg)` | ERROR 日志 |
| `self.send_alert(name, content)` | 钉钉告警 |
| `self.errback(failure)` | 默认错误回调（可覆盖） |

### 运行时属性

| 属性 | 说明 |
|------|------|
| `self.start_page` | 当前起始页（由 `-a` 传入） |
| `self.end_page` | 当前结束页（由 `-a` 传入） |
| `self.jobid` | 调度 Job ID |

---

## Pipeline 行为

### 自动注入字段

Pipeline 在入库时自动写入以下字段，Spider 无需手动处理：

| 字段 | 说明 |
|------|------|
| `spider_name` | 爬虫名 |
| `crawl_time` | 采集时间 |
| `created_time` | 入库时间 |

### 去重机制

`DedupPipeline` 根据 Spider 声明的 `dedup_fields` 查询目标表，已存在的记录跳过（`INSERT IGNORE`）。

### 写入其他表

```python
yield {
    'field1': 'value1',
    '_table': 'other_table',  # 覆盖 data_table，写入不同表
}
```

---

## custom_settings 常用项

```python
custom_settings = {
    'CONCURRENT_REQUESTS': 2,       # 并发数
    'DOWNLOAD_DELAY': 1,            # 下载延迟（秒）
    'COOKIES_ENABLED': True,        # 启用 Cookie
    'HTTPERROR_ALLOWED_CODES': [404, 500],  # 不抛异常的错误码
}
```
