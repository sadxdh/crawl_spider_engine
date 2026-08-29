import hashlib, scrapy
from urllib.parse import urlencode

import unicodedata

from spiders.base_spider import BaseSpider
from utils.mysql_tools import select_data
from utils.tools import *
from utils.time_kit import *

class CompanyHkStockTongHuaShunShareholdingSpider(BaseSpider):
    name = 'company_hkstock_tonghuashun_shareholding'
    data_table = 'listing_hk_major_shareholder'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 5, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        },
        # 'RETRY_ENABLED': True,
        # "RETRY_HTTP_CODES": [566],
        # "RETRY_TIMES": 3,  # 失败重试
        #'COOKIES_ENABLED': True  # 使用cookie字段必须得要
    }
    proxy_type = 'long_proxy'

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
        "sec-ch-ua": "\"Not=A?Brand\";v=\"99\", \"Google Chrome\";v=\"151\", \"Chromium\";v=\"151\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    def start_requests(self):
        code_list = select_data(
            table='stock_hk_hkex', data=['stock_code', 'stock_name'],
            suffix='GROUP BY stock_code ORDER BY stock_code'
        )
        for code in code_list:
            stock_code = code['stock_code']
            stock_name = code['stock_name']
            yield from self.get_details(stock_code[-4:], stock_code, stock_name)

    def get_details(self, req_code, stock_code, stock_name):
        url = f'https://stockpage.10jqka.com.cn/basicweb/176/HK{req_code}/holder.html'
        yield scrapy.Request(
            url=url,
            method="GET",
            headers=self.headers,
            callback=self.parse_details,
            cb_kwargs={'stock_code': stock_code, 'stock_name': stock_name, "req_code": req_code}
        )

    def parse_details(self, response, stock_code, stock_name, req_code):
        soup = BeautifulSoup(response.text, 'lxml')
        title = soup.select('[class="code fl"]>h1')[0].text.strip()
        if title and title == f"{unicodedata.normalize('NFKC', stock_name)}{stock_code}":
            for table_list in soup.select('[class="bd pt5"]>table'):
                publish_date = table_list.get('data-date')
                if publish_date:
                    for tbody_tr in table_list.select('tbody>tr'):
                        shareholder_name = tbody_tr.select('th')[0].text.strip() # 股东名称
                        finally_controller = tbody_tr.select('td')[0].text.strip()  # 最终控制人
                        shares_held_num = tbody_tr.select('td')[1].text.strip() # 持股数(万股)
                        shares_proportion = tbody_tr.select('td')[2].text.strip() # 占总股本比(%)
                        shareholding_changes = tbody_tr.select('td')[3].text.strip() # 持股变动(万股)
                        stock_type = tbody_tr.select('td')[4].text.strip() # 股票类型

                        main_item = {}
                        main_item['stock_code'] = stock_code
                        main_item['publish_date'] = publish_date
                        main_item['shareholder_name'] = shareholder_name
                        main_item['finally_controller'] = finally_controller
                        main_item['shares_held_num'] = shares_held_num
                        main_item['shares_proportion'] = shares_proportion
                        main_item['shareholding_changes'] = shareholding_changes
                        main_item['stock_type'] = stock_type
                        main_item['md5_value'] = hash_md5(f"{stock_code}{publish_date}{shareholder_name}")
                        yield main_item


        elif req_code != stock_code[:4]:
            yield from self.get_details(stock_code[:4], stock_code, stock_name)




    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')