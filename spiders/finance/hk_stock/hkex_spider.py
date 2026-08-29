import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.mysql_tools import select_data
from utils.tools import *
from utils.time_kit import *

# data_crawl_server spider/finance/hk_stock/hkex.py
class HkStockHkexSpider(BaseSpider):
    name = 'hk_stock_hkex'
    data_table = 'listing_info_ganggu'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        # 'DOWNLOADER_MIDDLEWARES': {
        #     'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        # }
    }
    proxy_type = 'no_proxy'

    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'referer': 'https://www.hkex.com.hk/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    }

    token_url = 'https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities'

    def start_requests(self):
        params = {
            'sc_lang': 'zh-cn',
        }
        separator = '&' if '?' in self.token_url else '?'
        request_url = f'{self.token_url}{separator}{urlencode(params)}'
        yield scrapy.Request(
            url=request_url,
            method='GET',
            headers=self.headers,
            callback=self.parse_token,
            dont_filter=True,
        )

    def parse_token(self, response):
        result = etree.HTML(response.body)
        script_list = xpath_parse(result, r'//script[not(src)]', return_list=True)
        result = [i for i in script_list if i.text is not None]
        res = [i.text for i in result if 'getToken' in i.text]
        token = match_text(res[0], 'return.*"(ev.*?)";') if res else None

        url = (f'https://www1.hkex.com.hk/hkexwidget/data/getequityfilter?lang=chn&token={token}&sort=5'
               f'&order=0&all=1&qid={return_timestamp()}&callback=null')
        yield scrapy.Request(
            url=url,
            method='GET',
            headers=self.headers,
            dont_filter=True,
            callback=self.parse_list,
        )

    def parse_list(self, response):
        result = match_text(response.text, r'null\((.*)\)')
        res = json.loads(result)
        datas = res['data']['stocklist']
        for data in datas:
            stock_code = data['ric']
            sym = data['sym']
            temp = {'stock_code': stock_code, 'sym': sym}
            yield from self.summary(temp)

    def summary(self, data):
        sym = data['sym']
        params = {'sym': sym, 'sc_lang': 'zh-cn'}
        separator = '&' if '?' in self.token_url else '?'
        request_url = f'{self.token_url}{separator}{urlencode(params)}'
        yield scrapy.Request(
            url=request_url,
            method='GET',
            headers=self.headers,
            callback=self.summary_token,
            dont_filter=True,
            cb_kwargs={'sym': sym}
        )

    def summary_token(self, response, sym):
        result = etree.HTML(response.body)
        script_list = xpath_parse(result, r'//script[not(src)]', return_list=True)
        result = [i for i in script_list if i.text is not None]
        res = [i.text for i in result if 'getToken' in i.text]
        token = match_text(res[0], 'return.*"(ev.*?)";') if res else None
        url = (f'https://www1.hkex.com.hk/hkexwidget/data/getequityquote?'
               f'sym={sym}&token={token}&lang=chn&qid={return_timestamp()}&callback=NULL')
        yield scrapy.Request(
            url=url,
            method='GET',
            headers=self.headers,
            dont_filter=True,
            callback=self.parse_detail,
        )

    def parse_detail(self, response):
        result = match_text(response.text, r'NULL\((.*)\)')
        res = json.loads(result)
        data = res['data']['quote']
        security_code_hk = data['ric']
        security_name = data['nm_s']
        mkt = data['mkt_cap']
        unit = data['mkt_cap_u']
        latest_market_value = mkt.replace(',', '') if mkt else None
        # entity_name = data['nm']
        # isin = data['isin']
        # listing_exchange = data['primaryexch']
        introduction = data.get('summary')

        ind_class = data.get('hsic_ind_classification')
        ind_class = ind_class.replace(' ', '') if ind_class else ''
        sub_class = data.get('hsic_sub_sector_classification')
        sub_class = sub_class if sub_class else ''
        hang_seng_industry = '-'.join([ind_class, sub_class])

        md5_value = self.search_data(security_code_hk)
        if md5_value:
            items = {}
            items['md5_value'] = md5_value
            items['security_name'] = security_name
            items['latest_market_value'] = latest_market_value
            items['unit'] = unit
            if introduction:
                items['introduction'] = introduction
            items['hang_seng_industry'] = hang_seng_industry
            # update_data(table_name='listing_info_ganggu', data=item)
            yield items

    def search_data(self, security_code):
        condition = f'security_code like "%{security_code}"'
        data = select_data(table='listing_info_ganggu', data=['security_code', 'md5_value'], condition=condition)
        return data[0]['md5_value'] if data else None

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')