"""AMAC 证券公司直投基金 → securities_company_direct_investment_fund"""
import hashlib
import random

import scrapy
from lxml import etree

from spiders.base_spider import BaseSpider
from utils.tools import *


_LIST_URL = 'https://gs.amac.org.cn/amac-infodisc/api/aoin/product?rand={r}&pageNo={p}&pageSize=20'



class DirectInvestSpider(BaseSpider):
    name = 'amac_direct_invest'
    data_table = 'securities_company_direct_investment_fund'
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

    def parse_item(self, details_tr_list):
        field_map = {
            '产品名称': 'product_name',
            '产品编码': 'product_code',
            '直投子公司名称': 'direct_investment_subsidiary',
            '管理机构名称': 'administration_mechanism',
            '设立日期': 'establishment_date',
            '备案日期': 'filing_date',
            '基金类型': 'fund_type',
            '组织形式': 'organizational_form',
            '运作状态': 'operation_status',
            '是否托管': 'whether_trusteeship',
            '托管人名称': 'trusteeship_name',
        }
        result = {var: '' for var in field_map.values()}
        # 获取标题
        for tr_data in details_tr_list:
            td_title = self.replace_data(tr_data.xpath('./td[@class="title"]/text()'))
            # 遍历字典，匹配标题并设置对应变量
            for title, var_name in field_map.items():
                if title in td_title:
                    result[var_name] = self.replace_data(tr_data.xpath('./td[2]/text()'))
                    break
        return result

    def replace_data(self, data):
        if data:
            return (data[0].strip().replace('\n', '').replace(u'\xa0', '').
                    replace("'", '`').replace('"', '”'))
        else:
            return ''

    def start_requests(self):
        url = f'https://gs.amac.org.cn/amac-infodisc/api/aoin/product?rand={random.random()}&page=0&size=20'
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
            details_url = f'https://gs.amac.org.cn/amac-infodisc/api/aoin/product?rand={random.random()}&page={page}&size=20'
            yield scrapy.Request(
                url=details_url,
                method="POST",
                headers=self.headers,
                body=json.dumps({}, separators=(",", ":")),
                callback=self.parse_list,
                dont_filter=True,
            )

    def parse_list(self, response):
        response = response.json()
        for content_data in reversed(response['content']):
            details_url = f"https://gs.amac.org.cn/amac-infodisc/res/aoin/product/{content_data['id']}.html"
            yield scrapy.Request(
                url=details_url,
                headers=self.headers,
                method="GET",
                callback=self.parse_urls,
                errback=self.errback,
                cb_kwargs={'details_url': details_url}
            )

    def parse_urls(self, response, details_url):
        details_lement = etree.HTML(response.body)
        details_tr_list = details_lement.xpath('//div[@class="info-body"]/div[1]/div'
                                               '[@class="table-response"]/table/tbody/tr')
        result = self.parse_item(details_tr_list)
        if result:
            product_name = result['product_name']
            product_code = result['product_code']
            direct_investment_subsidiary = result['direct_investment_subsidiary']
            administration_mechanism = result['administration_mechanism']
            establishment_date = result['establishment_date']
            filing_date = result['filing_date']
            fund_type = result['fund_type']
            organizational_form = result['organizational_form']
            operation_status = result['operation_status']
            whether_trusteeship = result['whether_trusteeship']
            trusteeship_name = result['trusteeship_name']

            # 构建入库字段
            md5_value = hash_md5(product_name + product_code)
            items = {}
            items['md5_value'] = md5_value
            items['product_name'] = product_name
            items['product_code'] = product_code
            items['direct_investment_subsidiary'] = direct_investment_subsidiary
            items['administration_mechanism'] = administration_mechanism
            items['establishment_date'] = establishment_date
            items['filing_date'] = filing_date
            items['fund_type'] = fund_type
            items['organizational_form'] = organizational_form
            items['operation_status'] = operation_status
            items['whether_trusteeship'] = whether_trusteeship
            items['trusteeship_name'] = trusteeship_name
            items['fund_url'] = details_url
            yield items
        else:
            self.log_error(f'私募基金产品数据为空，url：{details_url}')

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
