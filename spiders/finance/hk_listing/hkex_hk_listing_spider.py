"""港股上市爬虫，来源：东方财富"""
import scrapy
from spiders.base_spider import BaseSpider
from urllib.parse import urlencode, unquote

from utils.mysql_tools import select_data
from utils.tools import *


# https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities?sc_lang=zh-HK
class HkexHkListingSpider(BaseSpider):
    name = 'finance_hkex_hk_listing'
    data_table = 'stock_hk_hkex'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9',
        'referer': 'https://www.hkex.com.hk/',
        'sec-ch-ua': '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'script',
        'sec-fetch-mode': 'no-cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
    }
    datas_list = []

    def build_params(self, token):
        """qid / callback / _ 都基于当前时间戳动态生成，服务器不校验具体值。"""
        ts = int(time.time() * 1000)
        rand = ''.join(str(random.randint(0, 9)) for _ in range(20))
        callback = f"jQuery{rand}_{ts}"
        return {
            "lang": "chn",
            "token": token,
            "sort": "5",
            "order": "0",
            "all": "1",
            "qid": ts,
            "callback": callback,
            "_": ts,
        }

    def start_requests(self):
        url = "https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities?sc_lang=zh-HK"
        yield scrapy.Request(
            url=url,
            method="GET",
            headers=self.headers,
            callback=self.get_list,
            errback=self.errback,
        )

    def get_list(self, response):
        clean = re.sub(r'//.*', '', response.text)
        token = re.search(r'LabCI\.getToken\s*=\s*function.*?return\s*"([^"]+)"', clean, re.S).group(1)
        token = unquote(token)
        url = f"https://www1.hkex.com.hk/hkexwidget/data/getequityfilter?{urlencode(self.build_params(token))}"
        yield scrapy.Request(
            url=url,
            method="GET",
            headers=self.headers,
            callback=self.parse_list,
            errback=self.errback,
        )

    def parse_jsonp(self, text):
        """去掉 callback( ... ) 包裹，取中间完整 JSON。"""
        start = text.index('(') + 1
        end = text.rindex(')')
        return json.loads(text[start:end])

    def parse_list(self, response):
        result = self.parse_jsonp(response.text)
        datas = result['data']['stocklist']
        # 先全表插入
        for data in datas:
            stock_code = data['sym'].zfill(5)
            stock_name = data['nm']
            md5_value = hash_md5(str(stock_code))
            data_list = {'stock_code': stock_code, 'stock_name': stock_name, 'md5_value': md5_value, 'status': 1}
            yield from self.save_data(data_list)

        # 对比stock_hk表，在港交所里有，就为1，没有也插入为0
        table_datas = select_data(table='stock_hk', data=['entity_id', 'entity_name', 'status'])
        for table in table_datas:
            exists = 0
            if table['entity_id'] is None:
                continue
            for data in datas:
                if table['entity_id'] == data['sym'].zfill(5):
                    exists = 1
                    stock_code = data['sym'].zfill(5)
                    stock_name = data['nm']
                    md5_value = hash_md5(str(stock_code))
                    data_list = {'stock_code': stock_code, 'stock_name': stock_name, 'md5_value': md5_value, 'status': 1}
                    break
            if exists == 0:
                md5_value = hash_md5(str(table['entity_id']))
                data_list = {'stock_code': table['entity_id'], 'stock_name': table['entity_name'], 'md5_value': md5_value, 'status': 0}
            yield from self.save_data(data_list)

        # 更新数据，查询为1的数据，对比请求结果，不在现有结果的为0
        table_datas_2 = select_data(table='stock_hk_hkex', data=['stock_code', 'stock_name', 'status'], condition="status=1")
        for table in table_datas_2:
            exists = 0
            if table['stock_code'] is None:
                continue
            for data in datas:
                if table['stock_code'] == data['sym'].zfill(5):
                    exists = 1
                    break
            if exists == 0:
                md5_value = hash_md5(str(table['stock_code']))
                data_list = {'stock_code': table['stock_code'], 'stock_name': table['stock_name'], 'md5_value': md5_value, 'status': 0}
                yield from self.save_data(data_list)

    def save_data(self, data):
        stock_code = data['stock_code']
        stock_name = data['stock_name']
        md5_value = data['md5_value']
        status = data['status']

        items = {}
        items['stock_code'] = stock_code
        items['stock_name'] = stock_name
        items['status'] = status
        items['md5_value'] = md5_value
        # insert_data('stock_hk', item)
        yield items


    def errback(self, failure): self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
