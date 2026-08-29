"""票据违约公司查询 → entity_bill_default + bill_overdue_list
参照旧项目: data_crawl_server bill_file_spider.py
流程: 文章列表(分页) → 文章详情 → PDF下载 → pdfplumber解析 → 入库
"""
import hashlib, json, re, scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *
from utils.file_kit import *


class BillDefaultSpider(BaseSpider):
    name = 'economy_bill_default'
    data_table = ''
    dedup_fields = ['md5_value']
    default_end_page = 3
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Authorization': '',
        'Content-Type': 'application/json;charset=UTF-8',
        'Host': 'disclosure.shcpe.com.cn',
        'Origin': 'https://disclosure.shcpe.com.cn',
        'Referer': 'https://disclosure.shcpe.com.cn/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/127.0.0.0 Safari/537.36',
    }

    get_bill_file_url = 'https://disclosure.shcpe.com.cn/ent/public/article/list'
    detail_url = 'https://disclosure.shcpe.com.cn/ent/public/article/detail'
    download_file_url = 'https://disclosure.shcpe.com.cn/ent/public/file/fcms/download'

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            json_data = {"title": "", "current": page, "size": 10, "userType": "ADMIN", "typeCode": "acpt-overdue-list"}
            yield scrapy.JsonRequest(
                url=self.get_bill_file_url,
                method="POST",
                headers=self.headers,
                data=json_data,
                callback=self.parse,
                dont_filter=True,
            )

    def parse(self, response):
        result = response.json()['data']['dataList']
        for bill_file_data in result:
            article_id = bill_file_data['articleId']
            title = bill_file_data['title']

            md5_value = hash_md5(bill_file_data['title'])
            items = {}
            items['md5_value'] = md5_value
            items['title'] = title
            items['date_time'] = bill_file_data['publishTime']
            items['summary'] = bill_file_data['summary']
            items['_table'] = 'bill_overdue_list'
            # insert_data(table='bill_overdue_list', data=item)
            yield items

            yield from self.get_file_code(article_id, title)

    def get_file_code(self, article_id, title):
        detail_data = {'articleId': article_id}
        yield scrapy.JsonRequest(
            url=self.detail_url,
            method='POST',
            headers=self.headers,
            data=detail_data,
            callback=self.get_file,
            cb_kwargs={'title': title},
            dont_filter=True,
        )

    def get_file(self, response, data):
        """下载票据文件"""
        file_code = response.json()['data']['attachments'][0]['attachmentUrl']
        title = data['title']
        json_data = {
            'imgBatchNum': file_code,
        }
        yield scrapy.JsonRequest(
            url=self.download_file_url,
            method='POST',
            headers=self.headers,
            data=json_data,
            callback=self.parse_file,
            cb_kwargs={
                'title': title,
            },
            dont_filter=True,
        )

    def parse_file(self, file_response, title):
        """解析pdf入库"""
        text_list = extract_pdf_text(file_response.content)
        text = ''.join(text_list)
        lines = text.split('\n')

        query_time, due_date = self.handle_date(title)

        # 打印提取的文本
        for data in lines:
            try:
                text_list = data.split(' ')
                entity_name = text_list[1]
                social_credit_code = text_list[2]
                if not social_credit_code or '年' in social_credit_code or '统一' in social_credit_code:
                    continue
            except:
                continue
            md5_value = hash_md5(query_time+entity_name)
            items = {}
            items['md5_value'] = md5_value
            items['entity_name'] = entity_name
            items['unite_social_credit_code'] = social_credit_code
            items['query_time'] = query_time
            items['due_date'] = due_date
            items['_table'] = 'entity_bill_default'
            # insert_data(table='entity_bill_default', data=item)
            yield items

    @staticmethod
    def handle_date(title):
        date_str = match_text(title, r'截至(.*?)月')
        date_str = dispose_update_date(date_str)
        date_time = datetime.strptime(date_str, '%Y-%m')
        year_month = date_time.strftime('%Y-%m')

        date_str2 = match_text(title, r'截至(.*?)日')
        due_date = dispose_update_date(date_str2)
        return year_month, due_date

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url}')
