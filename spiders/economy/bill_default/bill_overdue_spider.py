"""票据逾期名单 → entity_bill_overdue"""
import hashlib, json, scrapy
from datetime import datetime
from spiders.base_spider import BaseSpider

_HDRS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Cache-Control': 'no-cache',
    'Content-Type': 'application/json;charset=UTF-8',
    'Host': 'disclosure.cpisp.shcpe.com.cn',
    'Origin': 'https://disclosure.shcpe.com.cn',
    'Pragma': 'no-cache',
    'Referer': 'https://disclosure.shcpe.com.cn/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Chromium";v="127"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

_LIST_URL = 'https://disclosure.cpisp.shcpe.com.cn/ent/public/article/list'
_DETAIL_URL = 'https://disclosure.cpisp.shcpe.com.cn/ent/public/article/detail'

def _md5(s):
    return hashlib.md5(str(s or '').encode()).hexdigest()


class BillOverdueSpider(BaseSpider):
    name = 'economy_bill_overdue'
    data_table = 'bill_overdue_list'
    dedup_fields = ['md5_value']
    allowed_domains = ['disclosure.cpisp.shcpe.com.cn', 'disclosure.shcpe.com.cn']
    default_end_page = 5

    custom_settings = {
        'CONCURRENT_REQUESTS': 2,
        'DOWNLOAD_DELAY': 1,
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            yield scrapy.Request(
                url=_LIST_URL, method='POST', headers=_HDRS,
                body=json.dumps({'title': '', 'current': page, 'size': 10,
                                'userType': 'ADMIN', 'typeCode': 'acpt-overdue-list'}),
                callback=self._parse_list, errback=self.errback)

    def _parse_list(self, response):
        try:
            items = response.json()['data']['dataList']
        except Exception:
            return
        for it in items:
            article_id = it.get('articleId')
            title = it.get('title', '')
            publish_time = it.get('publishTime', '')
            if not article_id:
                continue

            item = {
                'title': title,
                'date_time': publish_time,
                'summary': it.get('summary', ''),
                'md5_value': _md5(title),
            }
            yield item

            # Get detail for file code
            yield scrapy.Request(
                url=_DETAIL_URL, method='POST', headers=_HDRS,
                body=json.dumps({'articleId': article_id}),
                callback=self._parse_detail, errback=self.errback,
                meta={'article_id': article_id, 'title': title})

    def _parse_detail(self, response):
        try:
            attachments = response.json()['data']['attachments']
            if attachments:
                file_code = attachments[0].get('attachmentUrl', '')
                if file_code:
                    meta = response.meta
                    item = {
                        'title': f'附件-{meta["title"]}',
                        'file_code': file_code,
                        'md5_value': _md5(file_code),
                    }
                    yield item
        except Exception:
            pass

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
