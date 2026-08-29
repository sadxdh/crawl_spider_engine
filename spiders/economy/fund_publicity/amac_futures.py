"""AMAC 期货公司集合资管产品 → futures_products"""
import hashlib, random, scrapy
from utils.amac_fetch import amac_post
from spiders.base_spider import BaseSpider
from utils.tools import *

_LIST_URL = 'https://gs.amac.org.cn/amac-infodisc/api/pof/futures?rand={r}&page={p}&size=20'


def _md5(*p): return hashlib.md5(''.join(str(x or '') for x in p).encode()).hexdigest()


class FuturesSpider(BaseSpider):
    name = 'amac_futures'
    data_table = 'futures_products'
    allowed_domains = ['gs.amac.org.cn']
    default_end_page = 2
    custom_settings = {
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'
    dedup_fields = ['md5_value']
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Origin": "https://gs.amac.org.cn",
        # "Referer": "https://gs.amac.org.cn/amac-infodisc/res/cancelled/manager/index.html",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    def start_requests(self):
        url = f'https://gs.amac.org.cn/amac-infodisc/api/pof/futures?rand={random.random()}&page=0&size=20'
        yield scrapy.Request(
            url=url,
            method="POST",
            headers=self.headers,
            body=json.dumps({}, separators=(",", ":")),
            callback=self.parse_total_pages,
            dont_filter=True,
        )

    def parse_total_pages(self, response):
        if int(self.end_page) < 0:
            count_page = response.json()['totalPages']
            pages = [page for page in range(int(self.start_page) - 1, int(count_page))]
        else:
            pages = [page for page in range(int(self.start_page) - 1, int(self.end_page))]
        for page in pages:
            details_url = f'https://gs.amac.org.cn/amac-infodisc/api/pof/futures?rand={random.random()}&page={page}&size=20'
            yield scrapy.Request(
                url=details_url,
                method="POST",
                headers=self.headers,
                body=json.dumps({}, separators=(",", ":")),
                callback=self.parse_urls,
                dont_filter=True,
                cb_kwargs={'details_url': details_url}
            )

    def parse_urls(self, response, details_url):
        response = response.json()
        for content_data in response['content']:
            product_name = content_data['mpiName']
            product_code = content_data['mpiProductCode']
            administrator_name = content_data['aoiName']
            custodian_name = content_data['mpiTrustee']
            filing_date = content_data['registeredDate']
            establish_date = content_data['mpiCreateDate']
            due_date = content_data['dueDate']
            investment_type = content_data['tzlx']
            whether_classification = content_data['sfjgh']
            operation_status = content_data['fundStatus']
            url = f"https://gs.amac.org.cn/amac-infodisc/res/pof/futures/detail.html?id={content_data['id']}"

            md5_value = hash_md5(product_name + product_code)
            items = {}
            items['md5_value'] = md5_value
            items['product_name'] = product_name
            items['product_code'] = product_code
            items['administrator_name'] = administrator_name
            items['custodian_name'] = custodian_name
            items['filing_date'] = filing_date
            items['establish_date'] = establish_date
            items['due_date'] = due_date
            items['investment_type'] = investment_type
            items['whether_classification'] = whether_classification
            items['operation_status'] = operation_status
            items['fund_url'] = url
            yield items


    def errback(self, f): self.log_error(f'请求失败: {f.request.url}')
