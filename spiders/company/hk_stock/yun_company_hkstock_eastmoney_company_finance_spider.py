from scrapy import FormRequest
from spiders.base_spider import BaseSpider
from utils.mysql_tools import select_data
from utils.tools import *
from utils.time_kit import *
import time


class YunCaiWuFenXiSpider(BaseSpider):
    name = 'yun_company_hkstock_eastmoney_company_finance'
    headers = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Origin": "https://emweb.securities.eastmoney.com",
        "Referer": "https://emweb.securities.eastmoney.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
    }
    data_table = ''
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    def start_requests(self):
        url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        code_list = select_data(
            table='stock_hk_hkex', data=['stock_code'],
            suffix='GROUP BY stock_code ORDER BY stock_code'
        )
        for code in code_list:
            entity_id = code.get('stock_code')
            # 主要指标
            params = {
                "reportName": "RPT_HKF10_FN_MAININDICATOR",
                "columns": "ALL",
                "quoteColumns": "",
                "filter": f"(SECUCODE=\"{entity_id}.HK\")",
                "pageNumber": "1",
                "pageSize": "",
                "sortTypes": "-1",
                "sortColumns": "STD_REPORT_DATE",
                "source": "F10",
                "client": "PC",
            }
            yield FormRequest(
                url=url,
                method='get',
                headers=self.headers,
                formdata=params,
                callback=self.parse_detail,
                dont_filter=True
            )

            # 资产负债表
            params2 = {
                "reportName": "RPT_HKF10_FN_BALANCE_PC",
                "columns": "ALL",
                "quoteColumns": "",
                "filter": f"(SECUCODE=\"{entity_id}.HK\")",
                "pageNumber": "1",
                "pageSize": "",
                "sortTypes": "-1,1",
                "sortColumns": "REPORT_DATE,STD_ITEM_CODE",
                "source": "F10",
                "client": "PC",
            }
            yield FormRequest(
                url=url,
                method='get',
                headers=self.headers,
                formdata=params2,
                callback=self.parse_detail2,
            )

            # 利润表
            params3 = {
                "reportName": "RPT_HKF10_FN_INCOME_PC",
                "columns": "ALL",
                "quoteColumns": "",
                "filter": f"(SECUCODE=\"{entity_id}.HK\")",
                "pageNumber": "1",
                "pageSize": "",
                "sortTypes": "-1,1",
                "sortColumns": "REPORT_DATE,STD_ITEM_CODE",
                "source": "F10",
                "client": "PC",
            }
            yield FormRequest(
                url=url,
                method='get',
                headers=self.headers,
                formdata=params3,
                callback=self.parse_detail3,
            )

            # 现金流量表
            params4 = {
                "reportName": "RPT_HKF10_FN_CASHFLOW_PC",
                "columns": "ALL",
                "quoteColumns": "",
                "filter": f"(SECUCODE=\"{entity_id}.HK\")",
                "pageNumber": "1",
                "pageSize": "",
                "sortTypes": "-1,1",
                "sortColumns": "REPORT_DATE,STD_ITEM_CODE",
                "source": "F10",
                "client": "PC",
            }
            yield FormRequest(
                url=url,
                method='get',
                headers=self.headers,
                formdata=params4,
                callback=self.parse_detail4,
            )

    def parse_detail(self, response):
        """
        拿取详情数据，解析入库
        """
        result = response.json()['result']
        if result:
            data = result['data']
            for dt in data:
                STOCK_CODE = dt.get('SECUCODE')
                REPORT_DATE = dt.get('REPORT_DATE')
                STD_REPORT_DATE = dt.get('STD_REPORT_DATE')

                item = {}
                item['_table'] = 'listing_hk_leading_indicator'
                # item['table_comment'] = '港股企业财务分析数据'
                item['md5_value'] = hash_md5(STOCK_CODE + REPORT_DATE)

                item['stock_code'] = STOCK_CODE
                item['stock_name'] = dt.get('SECURITY_NAME_ABBR')
                item['publish_date'] = STD_REPORT_DATE
                item['real_publish_date'] = REPORT_DATE
                item['date_type_code'] = dt.get('DATE_TYPE_CODE')
                item['report_type'] = dt.get('REPORT_TYPE')
                item['operating_cf_per_share'] = dt.get('PER_NETCASH_OPERATE')
                item['revenue_per_share'] = dt.get('PER_OI')
                item['bps'] = dt.get('BPS')
                item['basic_eps'] = dt.get('BASIC_EPS')
                item['diluted_eps'] = dt.get('DILUTED_EPS')
                item['ttm_eps'] = dt.get('EPS_TTM')
                item['total_revenue'] = dt.get('OPERATE_INCOME')
                item['revenue_yoy_growth_pct'] = dt.get('OPERATE_INCOME_YOY')
                item['revenue_qoq_growth_pct'] = dt.get('OPERATE_INCOME_QOQ')
                item['gross_profit'] = dt.get('GROSS_PROFIT')
                item['gross_profit_yoy_growth_pct'] = dt.get('GROSS_PROFIT_YOY')
                item['gross_profit_qoq_growth_pct'] = dt.get('GROSS_PROFIT_QOQ')
                item['net_profit_parent'] = dt.get('HOLDER_PROFIT')
                item['net_profit_parent_yoy_growth_pct'] = dt.get('HOLDER_PROFIT_YOY')
                item['net_profit_parent_qoq_growth_pct'] = dt.get('HOLDER_PROFIT_QOQ')
                item['effective_tax_rate_pct'] = dt.get('TAX_EBT')
                item['operating_cf_to_revenue_pct'] = dt.get('OCF_SALES')
                item['avg_roe_pct'] = dt.get('ROE_AVG')
                item['annualized_roe_pct'] = dt.get('ROE_YEARLY')
                item['roa_pct'] = dt.get('ROA')
                item['gross_margin_pct'] = dt.get('GROSS_PROFIT_RATIO')
                item['net_margin_pct'] = dt.get('NET_PROFIT_RATIO')
                item['annualized_roi_pct'] = dt.get('ROIC_YEARLY')
                item['receivables_turnover'] = dt.get('ACCOUNTS_RECE_TDAYS')
                item['inventory_turnover'] = dt.get('INVENTORY_TDAYS')
                item['current_assets_turnover'] = dt.get('CURRENT_ASSETS_TDAYS')
                item['total_assets_turnover'] = dt.get('TOTAL_ASSETS_TDAYS')
                item['current_ratio'] = dt.get('CURRENT_RATIO')
                item['current_liabilities_to_total_liabilities_pct'] = dt.get('CURRENTDEBT_DEBT')
                item['debt_to_assets_ratio_pct'] = dt.get('DEBT_ASSET_RATIO')
                item['equity_multiplier'] = dt.get('EQUITY_MULTIPLIER')
                item['equity_ratio'] = dt.get('EQUITY_RATIO')
                yield item

    def parse_detail2(self, response):
        result = response.json()['result']
        if result:
            data = result['data']
            for dt in data:
                stock_code = dt.get('SECUCODE')
                report_date = dt.get('REPORT_DATE')
                item_name = dt.get('STD_ITEM_NAME')
                item = {}
                item['_table'] = 'listing_hk_asset_info'
                # item['table_comment'] = '港股企业资产信息数据'
                item['md5_value'] = hash_md5(stock_code + str(report_date) + str(item_name))
                item['stock_code'] = stock_code
                item['publish_date'] = report_date
                item['channel'] = item_name
                item['finance_type'] = 1
                item['content'] = json.dumps(dt)
                yield item

    def parse_detail3(self, response):
        result = response.json()['result']
        if result:
            data = result['data']
            for dt in data:
                stock_code = dt.get('SECUCODE')
                report_date = dt.get('REPORT_DATE')
                item_name = dt.get('STD_ITEM_NAME')
                item = {}
                item['_table'] = 'listing_hk_asset_info',
                # item['table_comment'] = '港股企业资产信息数据',
                item['md5_value'] = hash_md5(stock_code + str(report_date) + str(item_name)),
                item['stock_code'] = stock_code,
                item['publish_date'] = report_date,
                item['channel'] = item_name,
                item['finance_type'] = 2,
                item['content'] = json.dumps(dt)
                yield item

    def parse_detail4(self, response):
        result = response.json()['result']
        if result:
            data = result['data']
            for dt in data:
                stock_code = dt.get('SECUCODE')
                report_date = dt.get('REPORT_DATE')
                item_name = dt.get('STD_ITEM_NAME')
                item = {}
                item['_table'] = 'listing_hk_asset_info'
                # item['table_comment'] = '港股企业资产信息数据'
                item['md5_value'] = hash_md5(stock_code + str(report_date) + str(item_name))
                item['stock_code'] = stock_code
                item['publish_date'] = report_date
                item['channel'] = item_name
                item['finance_type'] = 3
                item['content'] = json.dumps(dt)
                yield item
