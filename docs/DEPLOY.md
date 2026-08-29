# 本地环境搭建

> 适用范围：爬虫引擎（crawl_spider_engine）｜最近更新：2026-08-28

## 1. 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10/11 |
| Python | 3.11+ |
| Git | 任意版本 |
| 网络 | 可访问 py.w.com（MySQL/Redis） |

## 2. 获取代码

```bash
git clone http://git.w.com:3000/crawler/crawl_spider_engine.git
cd crawl_spider_engine
```

## 3. 创建虚拟环境

```bash
# 创建
python -m venv .venv

# 激活
.venv\Scripts\activate
# 或 PowerShell: .venv\Scripts\Activate.ps1
```

## 4. 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：Scrapy、pymysql、redis、pdfplumber、py-mini-racer、pycryptodome、curl_cffi

### 常见安装问题

| 现象 | 解决 |
|------|------|
| `py-mini-racer` 安装失败 | 需要 Visual C++ Build Tools |
| `curl_cffi` 安装失败 | `pip install curl_cffi --only-binary=:all:` |
| `pip install` 超时 | 使用清华镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| Node.js 依赖缺失 | 安装 Node.js v22+：`winget install OpenJS.NodeJS.LTS` |

## 5. 配置 dev.ini

从模板创建并编辑：

```bash
cp config/dev.ini.example config/dev.ini
# 编辑 config/dev.ini，填写数据库和 Redis 连接信息

```ini
[MYSQL]
host = py.w.com
user = root
password = <开发库密码>
```

其余配置项（Redis、代理、LLM 等）按需填写，大部分爬虫只需 DB 配置。

## 6. 验证

```bash
# 列出所有爬虫
.venv/Scripts/python.exe -m scrapy list

# 试运行一个爬虫（1 页）
.venv/Scripts/python.exe -m scrapy crawl economy_bill_default -a start_page=1 -a end_page=1
```

## 7. 目录结构确认

```
crawl_spider_engine/
├── .venv/                  # 虚拟环境（gitignore）
├── scrapy.cfg
├── settings.py
├── config/dev.ini          # 需手动创建/编辑
├── spiders/                # 爬虫代码
├── middlewares/
├── pipelines/
├── extensions/
├── utils/
└── docs/                   # 本文档
```
