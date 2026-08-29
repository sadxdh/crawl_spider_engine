# Crawl Spider Engine — Claude 操作规范

## 核心约束

**只允许修改 `crawl_spider_engine` 目录内的文件，禁止读写任何其他项目。**

## 权限清单

| 操作 | 允许 | 禁止 |
|------|------|------|
| 读取/修改爬虫脚本 | ✅ `spiders/**/*.py` | — |
| 修改 pipelines/middlewares/extensions/utils | ✅ 谨慎修改 | — |
| 修改 config/dev.ini | ✅ 本地配置 | — |
| 修改 settings.py | ❌ | ❌ |
| 修改 config/prod.ini, docker.ini | ❌ | ❌ |
| 修改 Dockerfile, entrypoint.sh, setup.py | ❌ | ❌ |
| 修改 scrapy.cfg, requirements.txt | ❌ | ❌ |
| 修改 scripts/, docs/ | ❌ | ❌ |
| 数据库写操作 | ❌ | ❌ |
| 数据库只读查询 | ✅ SELECT | ❌ |
| 访问其他项目 | ❌ | ❌ |

## Spider 基类继承链

```
scrapy.Spider → BaseSpider (base_spider.py)
  ├── 经济类 Spider (直接继承)
  ├── FinanceBaseSpider (金融)
  ├── QyyjtBaseSpider (企业预警通 Token 管理)
  ├── LawBaseSpider (法律)
  └── NewsBaseSpider (资讯)
```

## 关键约定

1. **不使用 Scrapy Item 类** — 直接 `yield dict`
2. **Pipeline 只做 INSERT IGNORE** — 不建表、不改列
3. **spider_name / crawl_time 自动** — Pipeline 注入，Spider 不需处理
4. **增量运行** — `-a start_page=1 -a end_page=2`
5. **调度**: admin_server APScheduler (MySQL 持久化)，无 cron_runner
6. **代码更新**: git push → auto_deploy 自检测 → egg 热部署（不中断运行中 Job）
7. **去重**: DedupPipeline 基于 `dedup_fields` 做库内去重
8. **代理**: 默认 `no_proxy`，需要时显式设置 `proxy_type='tunnel_proxy'`

## 修复流程

1. 阅读 Spider 源码和旧项目参考
2. 本地测试: `scrapy crawl <name> -a start_page=1 -a end_page=1`
3. 推送代码: `git push`（auto_deploy 自动检测并热部署）
4. 手动验证: 触发 spider → 查看日志 → 检查数据库
