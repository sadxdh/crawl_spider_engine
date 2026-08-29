# 沪深京上市企业（东方财富）

东方财富网沪深京个股上市企业公开信息采集（企业信息 / 分红影响 / 高管 / 对外担保 / 股票发行 / 股权质押 / 股东信息 / 股本变动 / 股本构成 / 题材详情 / 股票代码），结果写入 `crawl_data` 库。

## 爬虫清单

| 任务名称 | 爬虫名称 | 数据库表 | 源文件 |
|---------|---------|---------|--------|
| 沪深京个股-企业信息 | basic_information_eastmoney | listing_entity_info | basic_information_eastmoney_spider.py |
| 沪深京个股-分红融资-分红影响 | dividend_impact_eastmoney | listing_stock_dividend_detail | dividend_impact_eastmoney_spider.py |
| 沪深京个股-高管信息 | executive_information_eastmoney | listing_stock_executive | executive_information_eastmoney_spider.py |
| 沪深京个股-对外担保 | external_guarantee_eastmoney | listing_stock_guarantee | external_guarantee_eastmoney_spider.py |
| 沪深京个股-股票发行 | issuance_process_eastmoney | listing_stock_issue | issuance_process_eastmoney_spider.py |
| 沪深京个股-股权质押 | share_pledge_eastmoney | listing_stock_pledge | share_pledge_eastmoney.py |
| 沪深京个股-股东信息 | shareholder_information_eastmoney | listing_stock_top_shareholder | shareholder_information_eastmoney_spider.py |
| 沪深京个股-股本结构-股份变动 | shares_changes_eastmoney | listing_stock_capital_changes | shares_changes_eastmoney_spider.py |
| 沪深京个股-股本结构-股本构成 | stock_composition_eastmoney | listing_stock_capital_structure | stock_composition_eastmoney_spider.py |
| 沪深京个股-题材详情 | subject_matter_eastmoney | listing_stock_subject_matter | subject_matter_eastmoney_spider.py |
| 沪深京个股-股票代码 | hsj_stock_code | stock_hsj | hsj_stock_code_spider.py |

## 运行方式

```bash
cd crawl_spider_engine
.venv/Scripts/python.exe -m scrapy crawl <spider_name> -a start_page=1 -a end_page=1
```
