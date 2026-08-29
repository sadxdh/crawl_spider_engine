# 中国基金业协会（AMAC）

中国证券投资基金业协会公开信息采集（会员 / 产品 / 私募基金管理人 / 登记办理流程 / 基金从业人员），结果写入 `crawl_data` 库。

## 爬虫清单

| 任务名称 | 爬虫名称 | 数据库表 | 源文件 |
|---------|---------|---------|--------|
| 基金协会-会员产品信息 | amac_member_search_all_product | private_equity_fund_products | amac_member_search_product_spider.py |
| 基金协会-会员信息 | amac_member_search_all | fund_association_member_info | amac_member_search_spider.py |
| 基金协会-私募基金管理人产品 | amac_private_fund_manager_product | private_equity_fund_products | amac_private_fund_manager_product_spider.py |
| 基金协会-私募基金管理人 | amac_private_fund_manager | private_fund_manager_info | amac_private_fund_manager_spider.py |
| 私募基金管理人登记办理流程公示 | amac_register_flow | private_fund_register_process | amac_register_flow.py |
| 基金协会-基金从业人员 | amac_fund_personnel_information | fund_practitioners_info | amac_fund_personnel_information_spider.py |

## 运行方式

```bash
cd crawl_spider_engine
.venv/Scripts/python.exe -m scrapy crawl <spider_name> -a start_page=1 -a end_page=1
```
