"""
法律风险-限制出境爬虫
数据来源：上海高院 hshfy.sh.cn
旧来源：data_crawl_server/law/legal_risk/shgjrmfy.py
"""
import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *


class LegalRiskSpider(BaseSpider):
    name = 'law_legal_risk'
    data_table = 'entity_limit_exit'
    dedup_fields = ['md5_value']

    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;'
                  'q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Referer': 'https://www.hshfy.sh.cn/shfy/web/channel_zx_list.jsp?pa=aemw9eHpjagPdcssPdcssz',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/128.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    domain = "https://www.hshfy.sh.cn/"
    url = "https://www.hshfy.sh.cn/shfy/web/channel_zx_list.jsp?pa=aemw9eHpjagPdcssPdcssz"
    # self.url = "https://www.hshfy.sh.cn/shfy/web/channel_zx_list.jsp?pa=aemw9eHpjagPdcssPdcssz"
    detail = "http://ccgp-liaoning.gov.cn/gateway/complaint_core/homePage/viewPubInfo/{}"

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            data = {
                'toPage': str(page),
                'fydm': '',
                'ah': '',
                'bzxr': '',
                'sqzxr': '',
            }
            yield scrapy.FormRequest(
                url=self.url,
                method='POST',
                headers=self.headers,
                formdata=data,
                callback=self.parse_list,
            )

    def parse_list(self, response):

        # content_list = []
        html = etree.HTML(response.text)
        article_a_list = html.xpath("//div[@class='list_a']/ul//li/a")
        for article in article_a_list:
            detail_link = article.xpath('./@href')[0]
            detail_url_list = f"https://www.hshfy.sh.cn/shfy/web/{detail_link}"
            yield scrapy.Request(
                url=detail_url_list,
                method='GET',
                headers=self.headers,
                callback=self.parse_detail,
            )


    def parse_detail(self, response):
        html = etree.HTML(response.text)
        data = {}
        for row in html.xpath("//div[@class='list_a']//td[@class='nr']/table//tr"):
            title = row.xpath('./td[1]//strong/text()')[0].strip()
            content = row.xpath('./td[2]/text()')[0].strip()
            if title == "承办法院、联系电话":
                parts = content.split()
                data["承办法院"] = parts[0]
                data["联系电话"] = parts[1]
            else:
                data[title] = content

        data_map = {
            "案号": "case_number",
            "被执行人": "limit_name",
            "被执行人地址": "executed_person_address",
            "执行标的金额（元）": "amount",
            "申请执行人": "applicant_name",
            "承办法院": "court_name",
            "联系电话": "court_phone"
        }
        new_data = {value: key for key, value in data_map.items()}

        for k, v in new_data.items():
            new_data[k] = data.get(v, '')

        items = {}
        # item.spider_name = self.spider_name
        items['case_number'] = new_data["case_number"]  # 案号
        items['limit_name'] = new_data["limit_name"]
        items['executed_person_address'] = new_data["executed_person_address"]
        items['amount'] = new_data["amount"]
        items['applicant_name'] = new_data["applicant_name"]
        items['court_name'] = new_data["court_name"]
        items['court_phone'] = new_data["court_phone"]

        items['md5_value'] = hash_md5(new_data["case_number"])

        # insert_data(table='entity_limit_exit', data=item)
        yield items