"""
汇率爬虫（exchange_rate）
数据来源：c-rates.com（所有货币对 USD 的汇率）

策略：
  每次全量抓取当天汇率页面，不分页
  去重字段：md5_value（currency2_code + release_date 的 md5）

本地调试：
  scrapy crawl finance_exchange_rate
"""

import scrapy
from datetime import datetime
from spiders.finance.exchange_rate.currency_name import currency_name_dict
from utils.tools import *
from spiders.base_spider import BaseSpider

# data_crawl_server spider/finance/exchange_rate/exchange_rate.py
class ExchangeRateSpider(BaseSpider):
    """汇率爬虫（c-rates.com）"""
    name = 'finance_exchange_rate'
    data_table = 'exchange_rate'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0",
        "referer": "https://www.c-rates.com/zh-cn/exchange-rates/usd.html",
    }

    release_time = datetime.now().strftime('%Y-%m-%d')

    def start_requests(self):
        url = "https://c-rates.com/USD"
        yield scrapy.Request(
            url=url,
            method='GET',
            headers=self.headers,
            callback=self.parse_list
        )

    def parse_list(self, response):
        try:
            element = etree.HTML(response.text)
            rows = xpath_parse(element, '//div[@class="regions-container"]//div[@class="regions-item"]', return_list=True)
            for row in rows:
                href = xpath_parse(row, './div/a[@class="regions-code"]/@href')
                source_url = urljoin(response.url, href)
                currency_code = xpath_parse(row, './div/a[@class="regions-code"]/text()')
                currency_name = currency_name_dict.get(currency_code)
                rate_value = xpath_parse(row, './div[@class="regions-rate"]/text()')

                if currency_name:
                    items = {}
                    items['currency1'] = '美元'
                    items['currency1_code'] = 'USD'
                    items['currency2'] = currency_name
                    items['currency2_code'] = currency_code
                    items['source_url'] = source_url
                    items['release_date'] = self.release_time
                    items['price'] = rate_value
                    items['change_percent'] = ''
                    items['md5_value'] = hash_md5(items['currency2_code'] + items['release_date'])
                    # insert_data(table='exchange_rate', data=item)
                    yield items
        except Exception as e:
            self.log_error(f'{self.name} 获取数据失败: {e}')
            # send_dd_msg(self.spider_name, '数据获取失败', f'汇率爬虫程序解析存储失败：{e}')

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
