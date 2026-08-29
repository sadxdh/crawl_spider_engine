from scrapy import FormRequest
from spiders.base_spider import BaseSpider
from utils.mysql_tools import select_data
from utils.tools import *
from utils.time_kit import *
import time



class YunShareholderSpider(BaseSpider):
    name = 'yun_company_hkstock_eastmoney_shareholder'
    default_origin_url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
    headers = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Origin": "https://emweb.securities.eastmoney.com",
        "Referer": "https://emweb.securities.eastmoney.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
    }
    data_table = 'listing_hk_shareholder'
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    def start_requests(self):
        code_list = select_data(
            table='stock_hk_hkex', data=['stock_code'],
            suffix='GROUP BY stock_code ORDER BY stock_code'
        )
        for code in code_list:
            stock_code = code['stock_code']
            params = {
                "reportName": "RPT_HKF10_EQUITYCHG_HOLDER",
                "columns": "ALL",
                "quoteColumns": "",
                "filter": f"(SECUCODE=\"{stock_code}.HK\")",
                "pageNumber": "1",
                "pageSize": "",
                "sortTypes": "-1,-1",
                "sortColumns": "EQUITY_TYPE,TOTAL_SHARES",
                "source": "F10",
                "client": "PC",
            }
            yield FormRequest(
                url=self.default_origin_url,
                method='get',
                headers=self.headers,
                formdata=params,
                callback=self.parse,
                dont_filter=True
            )

    def parse(self, response, **kwargs):

        result = response.json()
        result = result['result']
        if result:
            datas = result['data']
            for data in datas:
                stock_code = data['SECUCODE']
                shareholder = data['HOLDER_NAME']  # 持股方
                equity_type = data['EQUITY_TYPE']  # 权益类型
                report_date = data['REPORT_DATE']
                share = data['TOTAL_SHARES']   # 股份
                share_ratio = data['TOTAL_SHARES_RATIO']  # 股份占比
                share_type = data['SHARES_TYPE']  # 股份类型
                share_change_ratio = data['SHARES_CHG_RATIO']  # 股份变动
                direct_shareholding = data['DIRECT_SHARES']  # 直接持股
                equity_identity = data['HOLD_IDENTITY']  # 权益性质
                shareholding_method = data['IS_ZJ']  # 持股方式
                release_date = data['NOTICE_DATE']

                md5_value = hash_md5(stock_code+report_date+shareholder+equity_type+share_type)

                item = {}
                item['md5_value']=md5_value
                item['stock_code']=stock_code
                item['publish_date']=report_date
                item['release_date']=release_date
                item['shareholder']=shareholder
                item['equity_type']=equity_type
                item['share']=share
                item['share_ratio']=share_ratio
                item['share_type']=share_type
                item['share_change_ratio']=share_change_ratio
                item['direct_shareholding']=direct_shareholding
                item['shareholding_method']=shareholding_method
                item['equity_identity']=equity_identity
                yield item
