"""知识产权-国家知识产权局 → layout_design
参照旧项目 yuncrawl CnpiaPaiSpider:
  FormRequest POST → jpage/dataproxy.jsp → CDATA解析列表 → 详情页
"""
import hashlib, re, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *


class IntellectualPropertyRightSpider(BaseSpider):
    name = 'intellectual_property_right'
    data_table = 'honor_information'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'application/xml, text/xml, */*; q=0.01',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Host': 'www.cnipa.gov.cn',
        'Origin': 'https://www.cnipa.gov.cn',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/126.0.0.0 Safari/537.36',
    }
    base_url = 'https://www.cnipa.gov.cn/module/web/jpage/dataproxy.jsp'

    @staticmethod
    def generate_params(page):
        start = 1 if page == 1 else (page - 1) * 60 + 1
        end = 60 if start == 1 else start + 59
        params = {'startrecord': start, 'endrecord': end, 'perpage': '60'}
        return params


    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            data = {
                'col': '1',
                'webid': '1',
                'path': 'https://www.cnipa.gov.cn/',
                'columnid': '75',
                'sourceContentType': '1',
                'unitid': '485',
                'webname': '国家知识产权局',
                'permissiontype': '0',
            }
            params = self.generate_params(page)
            separator = "&" if "?" in self.base_url else "?"
            request_url = f"{self.base_url}{separator}{urlencode(params)}"
            yield scrapy.FormRequest(
                url=request_url,
                method="POST",
                headers=self.headers,
                formdata=data,
                callback=self.parse_list,
                dont_filter=True,
            )

    def parse_list(self, response):
        result = match_text(response.text, r'(<li>.*?</li>)')
        res = etree.HTML(result)
        rows = xpath_parse(res, '//li', return_list=True)
        for row in rows:
            title = xpath_parse(row, './a/text()')
            detail_url = xpath_parse(row, './a/@href')
            release_date = xpath_parse(row, './span/text()')
            temp = {'title': title, 'detail_url': detail_url, 'release_date': release_date}
            if '示范企业' in title or '优势企业' in title:
                yield scrapy.Request(
                    url=detail_url,
                    method="GET",
                    headers=self.headers,
                    callback=self.parse_detail,
                    cb_kwargs={'data': temp},
                )

    def parse_detail(self, response, data):
        result = etree.HTML(response.body)
        index_number = xpath_parse(result, '//table[@class="sls"]/tbody/tr[2]/td[1]/span/text()')
        document_number = xpath_parse(result, '//table[@class="sls"]/tbody/tr[4]/td[1]/span/text()')
        info_text = xpath_parse(result, '//div[@class="article-content cont"]/p//text()')
        rows = xpath_parse(result, '//div[@class="article-content cont"]/p/a', return_list=True)
        for row in rows:
            announcement_title = xpath_parse(row, './text()')
            href = xpath_parse(row, './href')
            announcement_url = urljoin(response.url, href)

            title = data['title']
            if '示范企业' in title:
                honor_name = '知识产权示范企业'
            elif '优势企业' in title:
                honor_name = '知识产权优势企业'
            else:
                honor_name = None
            release_date = data['release_date']
            md5_value = hash_md5(title + release_date + announcement_title)
            items = {}
            items['md5_value'] = md5_value
            items['honor_name'] = honor_name
            items['title'] = title
            items['company'] = '国家知识产权局'
            items['level'] = '国家级'
            items['release_date'] = release_date
            items['release_mechanism'] = '国家知识产权局运用促进司'
            items['index_number'] = index_number
            items['document_number'] = document_number
            items['info_text'] = info_text
            items['announcement_title'] = announcement_title
            items['announcement_url'] = announcement_url
            # insert_data(table='honor_information', data=item)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
