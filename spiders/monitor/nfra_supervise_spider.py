"""金融监管总局 → entity_nfra_supervise"""
import hashlib, re, scrapy
from lxml import etree
from spiders.base_spider import BaseSpider
from utils.tools import *


class NfraSuperviseSpider(BaseSpider):
    name = 'economy_nfra_supervise'
    data_table = 'enterprise_dynamics'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "If-Modified-Since": "Thu, 11 Sep 2025 02:19:34 GMT",
        "If-None-Match": "\"68c231b6-e8c3\"",
        "Referer": "https://www.nfra.gov.cn/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "sec-ch-ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    def start_requests(self):
        link_1 = 'https://www.nfra.gov.cn/cn/static/data/DocInfo/SelectDocByItemIdAndChild/data_itemId={id},pageIndex=1,pageSize=18.json'
        link_2 = 'https://www.nfra.gov.cn/cn/static/data/DocInfo/SelectDocByItemIdAndChild/data_itemId={id},pageIndex=1,pageSize=18.json'

        list1 = [{'行政许可': link_1.format(id=i)} for i in ['4110', '4111', '4112']]
        list2 = [{'行政处罚': link_2.format(id=i)} for i in ['4113', '4114', '4115']]
        list1.extend(list2)
        for res in list1:
            for channel, url in res.items():
                for page in range(self.start_page, self.end_page + 1):
                    url = url.replace('pageIndex=1', f'pageIndex={page}')
                    yield scrapy.Request(
                        url=url,
                        headers=self.headers,
                        method='GET',
                        dont_filter=True,
                        callback=self.parse,
                    )

    def parse(self, response):
        rows = response.json()['data']['rows']
        for row in rows:
            doc_id = row['docId']
            title = row['docSubtitle']
            url = f'https://www.nfra.gov.cn/cn/view/pages/ItemDetail.html?docId={doc_id}'
            release_time = row['publishDate']

            req_url = f'https://www.nfra.gov.cn/cn/static/data/DocInfo/SelectByDocId/data_docId={doc_id}.json'
            temp = {'title': title, 'url': url, 'release_time': release_time}
            yield scrapy.Request(
                url=req_url,
                headers=self.headers,
                method='GET',
                dont_filter=True,
                callback=self.parse_detail,
                cb_kwargs={'data': temp}
            )

    def parse_detail(self, response, data):
        text = response.json()['data']['docClob']
        result = etree.HTML(text)
        content = xpath_parse(result, '//div[@class="Section0"]/p//text()')
        if not content:
            # 解析table tr内的文本，对文本进行拼接
            element_list = xpath_parse(result, '//div[@class="Section0"]//table//tr')
            temp = []
            for ele in element_list:
                td_list = xpath_parse(ele, './/td')
                placeholder = ' ' if len(td_list) > 2 else ':'
                res = xpath_parse(ele, './/td//text()', placeholder=placeholder)
                if '序号' not in res:
                    temp.append(res)
            content = '，'.join(temp)

        website_name = '国家金融监督管理总局'

        items = {}
        items['release_time'] = data['release_time']
        items['title'] = data['title']
        items['url'] = data['url']
        items['content'] = content
        items['webname'] = website_name
        items['md5_value'] = hash_md5(data['title'] + data['release_time'] + website_name)
        yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
