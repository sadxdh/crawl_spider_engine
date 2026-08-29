# 建材物料信息

全国企业采购交易平台、生意社、生意社交易中心的建材物料信息采集，统一写入 `crawl_data.material_info` 表。

## 爬虫清单

| 任务名称 | 爬虫名称 | 数据库表 | 源文件 |
|---------|---------|---------|--------|
| 全国企业采购交易-建材物料信息 | economy_material_cneptp | material_info | material_cneptp_spider.py |
| 生意社-建材物料信息 | economy_www_100ppi_material | material_info | www100ppi_material_economy.py |
| 生意社交易中心-建材物料信息 | economy_material_rawmex | material_info | material_rawmex_spider.py |

## 运行方式

```bash
cd crawl_spider_engine
.venv/Scripts/python.exe -m scrapy crawl <spider_name> -a start_page=1 -a end_page=1
```
