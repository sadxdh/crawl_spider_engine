"""
东方财富股权融资（定向增发）爬虫
数据来源：https://data.eastmoney.com/other/qbzf.html

增量策略：
  - 每页50条，按 ISSUE_DATE 降序
  - 全量：start_page=1 end_page=20（约1000条历史记录）
  - 增量定时：start_page=1 end_page=2（最新100条，覆盖当日新增）
  - 去重字段：md5_value（stock_code + 类型 + issue_date 的 md5）

本地调试：
  scrapy crawl finance_east_money_stockright -a start_page=1 -a end_page=2
"""
import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *


# data_crawl_server spider/finance/stockright_finance/east_money.py
class EastMoneyStockrightSpider(BaseSpider):
    """东方财富股权融资定向增发 公开增发爬虫"""
    name = 'finance_east_money_stockright'
    data_table = 'entity_stockright_finance'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://data.eastmoney.com/other/qbzf.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0',
        'sec-ch-ua': '"Not)A;Brand";v="99", "Microsoft Edge";v="127", "Chromium";v="127"',
    }

    # base_url = ('https://datacenter-web.eastmoney.com/api/data/v1/get?sortColumns=ISSUE_DATE&sortTypes=-1'
    #             '&pageSize=50&pageNumber={}&reportName=RPT_SEO_DETAIL'
    #             '&columns=ALL&quoteColumns=f2~01~SECURITY_CODE~NEW_PRICE'
    #             '&quoteType=0&source=WEB&client=WEB&filter=(SEO_TYPE%3D%221%22)')
    base_url = ('https://datacenter-web.eastmoney.com/api/data/v1/get?sortColumns=ISSUE_DATE&sortTypes=-1'
                '&pageSize=50&pageNumber={}&reportName=RPT_SEO_DETAIL'
                '&columns=ALL&quoteColumns=f2~01~SECURITY_CODE~NEW_PRICE'
                '&quoteType=0&source=WEB&client=WEB')

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            url = self.base_url.format(page)
            yield scrapy.Request(
                url=url,
                method='GET',
                headers=self.headers,
                callback=self.parse_list,
            )

    def parse_list(self, response):
        result = response.json()
        datas = result['result']['data']
        for data in datas:
            stock_code = data['SECURITY_CODE']
            stock_name = data['SECURITY_NAME_ABBR']
            financing_content = data['PRICE_PRINCIPLE']
            issue_date = data['ISSUE_LISTING_DATE']
            issue_price = data['ISSUE_PRICE']
            issue_volume = self.calculate_amount(data['ISSUE_NUM'])
            fundraising_amount = self.calculate_amount(data['NET_RAISE_FUNDS'])
            if data['SEO_TYPE'] == "1":
                md5_value = hash_md5(stock_code + '股权融资定向增发已实施' + issue_date)
                mode = '定向增发'
            elif data['SEO_TYPE'] == "2":
                md5_value = hash_md5(stock_code + '股权融资公开增发已实施' + issue_date)
                mode = '公开增发'
            else:
                continue

            items = {}
            items['stock_code'] = stock_code
            items['stock_name'] = stock_name
            items['financing_type'] = '股权融资'
            items['financing_content'] = financing_content
            items['schedule'] = '已实施'
            items['mode'] = mode
            items['issue_date'] = issue_date
            items['plan_issue_price'] = issue_price
            items['issue_price'] = issue_price
            items['plan_issue_volume'] = issue_volume
            items['issue_volume'] = issue_volume
            items['plan_fundraising_amount'] = fundraising_amount
            items['fundraising_amount'] = fundraising_amount
            items['md5_value'] = md5_value
            # insert_data('entity_stockright_finance', item)
            yield items

    @staticmethod
    def calculate_amount(value):
        # 将值转为亿元
        return int(value) / 100000000 if value else None



    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} - {failure.value}')
