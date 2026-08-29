# 爬虫开发指南

> 适用范围：爬虫引擎（crawl_spider_engine）｜最近更新：2026-08-28

## 修改权限

> 核心原则：**保证线上环境不受影响**。改动影响范围越大，越需谨慎。

### 可自由修改

| 目录/文件 | 说明 |
|-----------|------|
| `spiders/**/*.py` | 爬虫脚本，只影响单个爬虫 |

### 可修改，但影响所有爬虫（需充分测试）

| 目录/文件 | 说明 |
|-----------|------|
| `pipelines/` | 数据管道（去重/统计/入库） |
| `middlewares/` | 下载中间件（UA/代理/Cookie/重试） |
| `extensions/` | 扩展（心跳/统计） |
| `utils/` | 工具库（MySQL/Redis/钉钉/LLM/代理） |
| `config/dev.ini` | 本地开发配置（从 `dev.ini.example` 复制，gitignore） |

### 禁止修改（影响线上容器运行）

| 目录/文件 | 说明 |
|-----------|------|
| `settings.py` | Scrapy 全局配置入口 |
| `config/prod.ini` | 生产配置（连接信息） |
| `Dockerfile` | 容器构建定义 |
| `entrypoint.sh` | 容器启动脚本（含自检测热部署） |
| `setup.py` | egg 打包配置 |
| `scrapy.cfg` | Scrapyd 部署配置 |
| `scripts/` | 部署/迁移/自检测脚本 |
| `requirements.txt` | 项目依赖 |
| `.gitattributes` | Git 行尾配置 |
| `docs/` | 项目文档 |
| 其他项目目录 | `crawl_admin_server`、`crawl_admin_web` 等 |

### 数据库

| 操作 | 允许 | 禁止 |
|------|------|------|
| SELECT 查询 | ✅ | — |
| INSERT/UPDATE/DELETE | — | ❌ |
| CREATE/ALTER/DROP | — | ❌ |

## 最小 Spider

```python
import hashlib, scrapy
from spiders.base_spider import BaseSpider

_HDRS = {'User-Agent': 'Mozilla/5.0'}

class MySpider(BaseSpider):
    name = 'economy_my_spider'
    data_table = 'target_table'
    dedup_fields = ['md5_value']
    allowed_domains = ['example.com']
    default_end_page = 3

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            yield scrapy.Request(
                url=f'https://example.com/list?page={page}',
                headers=_HDRS, callback=self.parse, errback=self.errback)

    def parse(self, response):
        for row in response.css('.item'):
            name = row.css('.title::text').get('').strip()
            if not name:
                continue
            yield {
                'entity_name': name,
                'announcement_title': row.css('.desc::text').get('').strip(),
                'release_date': row.css('.date::text').get('').strip(),
                'source': '示例来源',
                'md5_value': hashlib.md5(name.encode()).hexdigest(),
            }

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
```

## 数据格式

直接 `yield dict`，Pipeline 自动处理。`spider_name`、`crawl_time`、`created_time` 自动注入。

```python
yield {
    'field1': 'value1',          # 业务字段
    'field2': 'value2',
    'md5_value': '...',          # 去重字段（必填，对应 dedup_fields）
    '_table': 'other_table',     # 可选：写入不同表
}
```

## 基类属性

| 属性 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `name` | str | — | 唯一标识 `{category}_{name}` |
| `data_table` | str | — | MySQL 表名 |
| `dedup_fields` | list | [] | 去重字段（对应 item 中的 key） |
| `allowed_domains` | list | — | Scrapy 允许的域名 |
| `proxy_type` | str | `no_proxy` | `no_proxy` / `tunnel_proxy` |
| `default_start_page` | int | 1 | 默认起始页 |
| `default_end_page` | int | 100 | 默认结束页 |
| `custom_settings` | dict | — | 覆盖 settings.py |

## custom_settings 常用项

```python
custom_settings = {
    'CONCURRENT_REQUESTS': 2,       # 并发数
    'DOWNLOAD_DELAY': 1,            # 下载延迟（秒）
    'COOKIES_ENABLED': True,        # 启用 Cookie
    'HTTPERROR_ALLOWED_CODES': [404, 500],  # 允许的错误码
}
```

## 基类方法

| 方法 | 说明 |
|------|------|
| `self.start_page` | 当前起始页（通过 `-a start_page=N` 传入） |
| `self.end_page` | 当前结束页 |
| `self.jobid` | 调度 Job ID |
| `self.page_urls(template)` | 生成分页 URL 列表 `template.format(page=N)` |
| `self.log_info(msg)` | INFO 日志 |
| `self.log_warning(msg)` | WARNING 日志 |
| `self.log_error(msg)` | ERROR 日志 |
| `self.send_alert(name, content)` | 发送钉钉告警 |

## JSON API 爬虫

```python
def parse(self, response):
    data = response.json()
    for item in data.get('data', []):
        if not item.get('name'):
            continue
        yield {
            'name': item['name'],
            'value': item.get('value', ''),
            'md5_value': hashlib.md5(item['name'].encode()).hexdigest(),
        }
```

## HTML 爬虫（lxml）

```python
from lxml import etree

def parse(self, response):
    tree = etree.HTML(response.body)
    for row in tree.xpath('//div[@class="list"]/ul/li'):
        title = ''.join(row.xpath('./a/text()')).strip()
        href = row.xpath('./a/@href')[0] if row.xpath('./a/@href') else ''
        if not title:
            continue
        yield scrapy.Request(
            url=response.urljoin(href),
            callback=self.parse_detail, errback=self.errback,
            meta={'title': title})

def parse_detail(self, response):
    title = response.meta['title']
    tree = etree.HTML(response.body)
    content = ' '.join(tree.xpath('//div[@class="content"]//text()'))
    yield {
        'title': title,
        'content': content[:5000],
        'md5_value': hashlib.md5(title.encode()).hexdigest(),
    }
```

## 特殊场景

### 需要代理

```python
proxy_type = 'tunnel_proxy'  # 走隧道代理
```

### Token 登录（企业预警通）

```python
from spiders.finance.qyyjt.qyyjt_base_spider import QyyjtBaseSpider


class MySpider(QyyjtBaseSpider):
    name = 'finance_my_spider'
    _BASE_HEADERS = {...}

    def start_requests(self):
        headers = self._get_auth_headers()  # 自动注入 Token
        if not headers:
            return
        yield scrapy.Request(...)
```

### 需要 Cookie（法院案例）

```python
from spiders.law.law_case_auth import generate_cookie
import redis, random

r = redis.Redis(...)
accounts = r.hgetall('law_case:account_info')
phone = random.choice(list(accounts.keys()))
cookies = generate_cookie(phone, accounts[phone])

yield scrapy.Request(url=..., cookies=cookies, ...)
```

## 本地调试

```bash
# 基本调试
.venv/Scripts/python.exe -m scrapy crawl economy_my_spider -a start_page=1 -a end_page=2

# DEBUG 日志
.venv/Scripts/python.exe -m scrapy crawl economy_my_spider -a start_page=1 -a end_page=1 -s LOG_LEVEL=DEBUG

# 输出 JSON 验证数据（不写库）
.venv/Scripts/python.exe -m scrapy crawl economy_my_spider -a start_page=1 -a end_page=1 -o test.json
```

## 开发流程

```bash
# 1. 创建爬虫文件
# spiders/<category>/my_spider.py

# 2. 本地测试
.venv/Scripts/python.exe -m scrapy crawl <spider_name> -a start_page=1 -a end_page=1

# 3. 验证数据正确 → 提交
git add spiders/<category>/my_spider.py
git commit -m 'feat: 新增xx爬虫'
git push
```
