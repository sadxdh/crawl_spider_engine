# 港股上市公司（东方财富 / 同花顺）

东方财富网、同花顺港股上市公司数据采集（财务分析 / 公司概况 / 董事高管 / 股东信息 / 股本结构 / 持股股东），结果写入 `crawl_data` 库。

## 爬虫清单

| 任务名称 | 爬虫名称 | 数据库表 | 源文件 |
|---------|---------|---------|--------|
| 港股公司-财务分析 | yun_company_hkstock_eastmoney_company_finance | listing_hk_asset_info | yun_company_hkstock_eastmoney_company_finance_spider.py |
| 港股公司-公司概况 | yun_company_hkstock_eastmoney_profile | listing_hk_entity_info | yun_company_hkstock_eastmoney_profile_spider.py |
| 港股公司-董事高管 | yun_company_hkstock_eastmoney_director_executive | listing_hk_director_executive | yun_company_hkstock_eastmoney_director_executive_spider.py |
| 港股公司-股东信息 | yun_company_hkstock_eastmoney_shareholder | listing_hk_shareholder | yun_company_hkstock_eastmoney_shareholder_spider.py |
| 港股公司-股本结构 | company_hkstock_eastmoney_shareholding_structure | listing_hk_capital_structure | company_hkstock_eastmoney_shareholding_structure_spider.py |
| 港股公司-持股股东 | company_hkstock_tonghuashun_shareholding | listing_hk_major_shareholder | company_hkstock_tonghuashun_shareholding_spider.py |

## 运行方式

```bash
cd crawl_spider_engine
.venv/Scripts/python.exe -m scrapy crawl <spider_name> -a start_page=1 -a end_page=1
```
