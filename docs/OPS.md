# 本地调试 & 排错

> 适用范围：爬虫引擎（crawl_spider_engine）｜最近更新：2026-08-28

## 调试命令

```bash
# 列出所有爬虫
.venv/Scripts/python.exe -m scrapy list

# 单页测试（最常用）
.venv/Scripts/python.exe -m scrapy crawl <spider_name> -a start_page=1 -a end_page=1

# DEBUG 日志
.venv/Scripts/python.exe -m scrapy crawl <spider_name> -a start_page=1 -a end_page=1 -s LOG_LEVEL=DEBUG

# 只运行不写入数据库（需临时去掉 MysqlPipeline）
.venv/Scripts/python.exe -m scrapy crawl <spider_name> -a start_page=1 -a end_page=1 -o output.json
```

## 日志

Scrapy 输出到控制台（stdout），日志级别由 `settings.py` 的 `LOG_LEVEL` 控制。

```
# 日志格式
2026-06-04 10:00:00 [scrapy.core.engine] INFO: Spider opened
2026-06-04 10:00:01 [scrapy.core.engine] DEBUG: Crawled (200) <GET https://...>
2026-06-04 10:00:02 [pipelines.MysqlPipeline] INFO: 写入 50 条记录到 crawl_data.xxx
2026-06-04 10:00:03 [scrapy.core.engine] INFO: Spider closed (finished)
```

### Spider 内打日志

```python
self.log_info(f'正在处理第 {page} 页')
self.log_warning(f'响应状态异常: {response.status}')
self.log_error(f'请求失败: {url}')
```

## 常见问题

### 数据库连接失败

```
pymysql.err.OperationalError: (2003, "Can't connect to MySQL server")
```

→ 检查 `config/dev.ini` 中数据库地址和密码是否正确，确认 VPN 已连接。

### Spider 无输出

可能原因：
1. **目标网站改版** → 检查选择器是否失效，用 `response.text` 打印页面内容
2. **反爬拦截** → 检查是否需要代理或 Cookie，查看 `response.status`
3. **分页参数错误** → 确认 `start_page` / `end_page` 范围

### 调试技巧

```python
def parse(self, response):
    # 打印页面 HTML 前 500 字符
    print(response.text[:500])

    # 打印响应头
    print(dict(response.headers))

    # 只取第一个列表项验证选择器
    first = response.css('.item').get()
    if not first:
        self.log_error('选择器未匹配到数据，可能页面改版')
        return
```

### py_mini_racer / Node.js 相关错误

部分金融类爬虫（`FinanceBaseSpider`）依赖 Node.js 执行 JS 签名。确保安装了 Node.js v22+，且 `config/dev.ini` 中 `[NODE]` 配置正确。

### 代理相关

```python
# 需要代理时设置
proxy_type = 'tunnel_proxy'

# 不需要代理（默认）
proxy_type = 'no_proxy'
```

如果不确定是否需要代理，先用 `no_proxy` 试跑一页看能否正常返回数据。

## 性能调优

```python
# 对目标网站友好的低速配置
custom_settings = {
    'CONCURRENT_REQUESTS': 1,
    'DOWNLOAD_DELAY': 2,
}

# 高吞吐配置
custom_settings = {
    'CONCURRENT_REQUESTS': 32,
    'DOWNLOAD_DELAY': 0,
}
```

## 快速操作卡

```bash
# 列出爬虫
.venv/Scripts/python.exe -m scrapy list

# 测试单页
.venv/Scripts/python.exe -m scrapy crawl <name> -a start_page=1 -a end_page=1

# 测试并输出 JSON（不写库）
.venv/Scripts/python.exe -m scrapy crawl <name> -a start_page=1 -a end_page=1 -o test.json

# DEBUG 模式
.venv/Scripts/python.exe -m scrapy crawl <name> -a start_page=1 -a end_page=1 -s LOG_LEVEL=DEBUG
```
