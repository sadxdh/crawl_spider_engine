import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *


class DfcfIpofileHsjSpider(BaseSpider):
    name = 'dfcf_ipofile_hsj_spider'
    data_table = 'ipo_pdf'
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
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Referer': 'https://data.eastmoney.com/notices/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            params = {
                'cb': '',
                'sr': '-1',
                'page_size': '50',
                'page_index': str(page),
                'ann_type': 'SHA,CYB,SZA,BJA,INV',
                'client_source': 'web',
                'f_node': '0',
                's_node': '0',
            }

            url = 'https://np-anotice-stock.eastmoney.com/api/security/ann'
            request_url = f'{url}?{urlencode(params)}'

            yield scrapy.Request(
                url=request_url,
                method='GET',
                headers=self.headers,
                callback=self.get_urls,
                dont_filter=True,
            )

    def get_urls(self, response):
        """得到每个ipo的数据"""
        json_data = response.json()
        announcements_list = json_data.get('data', {}).get('list', [])
        # 循环遍历整页ipo公告list中的每条元素
        for announcement in announcements_list:
            art_code = announcement['art_code']
            i = 1 if len(announcement['codes']) > 1 else 0
            short_name = announcement['codes'][i]['short_name']
            stock_code = announcement['codes'][i]['stock_code']
            column_name = announcement['columns'][0]['column_name']
            title = announcement['title']
            notice_date = announcement['notice_date']
            url = f'https://data.eastmoney.com/notices/detail/{stock_code}/{art_code}.html'
            result = {
                'ipo_type': '沪深京A股公告',
                'short_name': short_name,
                'stock_code': stock_code,
                'column_name': column_name,
                'title': title,
                'source_url': url,
                'notice_date': notice_date,
                'art_code': art_code,
            }
            params = {
                'cb': '',
                'art_code': result['art_code'],
                'client_source': 'web',
            }
            headers = {
                'Referer': 'https://data.eastmoney.com/notices/detail/002017/AN202505051667811636.html',
            }
            url = 'https://np-cnotice-stock.eastmoney.com/api/content/ann'
            request_url = f'{url}?{urlencode(params)}'

            yield scrapy.Request(
                url=request_url,
                method='GET',
                headers=headers,
                callback=self.url_parse,
                cb_kwargs={'result': result},
                dont_filter=True,
            )

    def url_parse(self, response, result):
        # 可从获取result函数内取得display_time值构造pdf链接所需的时间戳
        if response:
            try:
                json_data = response.json()
                pdf_url = json_data.get('data', {}).get('attach_list', [])[0].get('attach_url', [])
                items = {}
                md5_value = hash_md5(pdf_url)
                items['md5_value'] = md5_value
                items['ipo_type'] = result['ipo_type']
                items['code'] = result['stock_code']
                items['announcement_title'] = result['title']
                items['announcement_url'] = pdf_url
                items['code_name'] = result['short_name']
                items['release_time'] = result['notice_date']
                items['source_url'] = result['source_url']
                items['column_name'] = result['column_name']
                # insert_data(table='ipo_pdf', data=item)
                yield items
            except Exception as e:
                self.log_error(f'解析ipo文件详情页失败，错误：{e},url:{result["url"]}')

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
