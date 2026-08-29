"""AMAC 已注销私募基金管理人 → cancel_the_fund_manager"""
import hashlib
import json
import random

import scrapy
from lxml import etree
from spiders.base_spider import BaseSpider
from utils.tools import *


_LIST_URL = 'https://gs.amac.org.cn/amac-infodisc/api/pof/cancelledFund?rand={r}&page={p}&size=20'


class CancelledSpider(BaseSpider):
    name = 'amac_cancelled'
    data_table = 'cancel_the_fund_manager'
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

    def replace_data(self, data):
        if data:
            return (data[0].strip().replace('\n', '').replace(u'\xa0', '').
                    replace("'", '`').replace('"', '”'))
        else:
            return ''

    def extract_information(self, tr_data, fields):
        return {field_name: self.replace_data(tr_data.xpath(f'./td[{index + 1}]/text()')) for index, field_name in
                enumerate(fields)}

    def parse_item(self, details_tr_list):
        field_map = {
            '基金管理人全称(中文)': 'manager_name',
            '统一社会信用代码': 'unified_credit_code',
            '注册地址': 'registration_location',
            '办公地址': 'office_location',
            '注册资本(万元)人民币': 'registered_capital',
            '实缴资本(万元)人民币': 'Paid_in',
            '企业性质': 'Enterprise_nature',
            '机构类型': 'organization_type',
            '机构网址': 'mechanism_website',
        }
        result = {var: '' for var in field_map.values()}
        # 获取标题
        for tr_data in details_tr_list:
            td_title = self.replace_data(tr_data.xpath('./td[1]/text()'))
            # 遍历字典，匹配标题并设置对应变量
            for title, var_name in field_map.items():
                if title in td_title:
                    text1 = self.replace_data(tr_data.xpath('./td[2]/text()'))
                    text2 = self.replace_data(tr_data.xpath('./td[2]/span/text()'))
                    result[var_name] = text1 if text1 else text2
                    break
        return result


    def start_requests(self):
        url = f'https://gs.amac.org.cn/amac-infodisc/api/cancelled/manager?rand={random.random()}&page=0&size=20'
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
            details_url = f'https://gs.amac.org.cn/amac-infodisc/api/cancelled/manager?rand={random.random()}&page={page}&size=20'
            yield scrapy.Request(
                url=details_url,
                method="POST",
                headers=self.headers,
                body=json.dumps({}, separators=(",", ":")),
                callback=self.parse_urls,
                dont_filter=True,
            )

    def parse_urls(self, response):
        response = response.json()
        for content_data in response['content']:
            url = f"https://gs.amac.org.cn/amac-infodisc/res/cancelled/manager/{content_data['userTenantId']}.html"
            yield scrapy.Request(
                url=url,
                method="GET",
                headers=self.headers,
                callback=self.parse_items,
                cb_kwargs={'url': url},
            )

    def parse_items(self, response, url):
        details_element = etree.HTML(response.body)
        cancellation_tr_list = details_element.xpath(
            '//div[@class="info-body"]/div/div[1]/div[1]/table/tbody/tr')
        cancellation_date = self.replace_data(cancellation_tr_list[0].xpath('./td[2]/text()'))
        cancellation_type = self.replace_data(cancellation_tr_list[1].xpath('./td[2]/text()'))
        manager_info_tr_list = details_element.xpath(
            '//div[@class="info-body"]/div/div[1]/div[3]/table/tbody/tr')
        data = self.parse_item(manager_info_tr_list)
        actual_controller = self.replace_data(
            details_element.xpath('//div[@class="info-body"]/div/div[2]/div[2]'
                                  '/table/tbody/tr/td[2]/text()'))
        # 高管信息
        executive_information = [
            self.extract_information(executive_tr_data, ['serial_number', 'post', 'name'])
            for executive_tr_data in
            details_element.xpath(
                '//div[@class="info-body"]/div/div[3]/div[2]/table/tbody/tr/td[2]/table/tbody/tr')
        ]

        # 关联方信息（仅包含关联私募基金管理人）
        related_party_information = [
            self.extract_information(related_tr_data,
                                     ['serial_number', 'type', 'name', 'register_number', 'credit_code'])
            for related_tr_data in
            details_element.xpath(
                '//div[@class="info-body"]/div/div[4]/div[2]/table/tbody/tr/td[2]/table/tbody/tr')
        ]

        # 出资人信息
        investor_information = [
            self.extract_information(investor_tr_data, ['serial_number', 'name', 'comparison_column'])
            for investor_tr_data in
            details_element.xpath(
                '//div[@class="info-body"]/div/div[5]/div[2]/table/tbody/tr/td[2]/table/tbody/tr')
        ]

        # 产品信息
        product_information = {}

        # 注销时已清算产品列表
        cleared_products = [
            self.extract_information(cleared_tr_data,
                                     ['serial_number', 'business_circles_date', 'filing_fund_name',
                                      'Previously_filed_date', 'type', 'custodian_name'])
            for cleared_tr_data in details_element.xpath(
                '//div[@class="info-body"]/div/div[6]/div[2]/table/tbody/tr[1]/td[2]/table/tbody/tr')
        ]
        product_information['cleared_products'] = cleared_products

        # 注销时未在系统提交清算的产品
        unclear_products = [
            self.extract_information(unclear_tr_data,
                                     ['serial_number', 'business_circles_date', 'filing_fund_name',
                                      'Previously_filed_date', 'type', 'custodian_name'])
            for unclear_tr_data in details_element.xpath(
                '//div[@class="info-body"]/div/div[6]/div[2]/table/tbody/tr[2]/td[2]/table/tbody/tr')
        ]
        product_information['unclear_products'] = unclear_products
        (manager_name, unified_credit_code, registration_location, office_location, registered_capital,
         Paid_in, Enterprise_nature, organization_type, mechanism_website) = data.values()
        md5_value = hash_md5(manager_name + unified_credit_code)
        items = {}
        items['md5_value'] = md5_value
        items['cancellation_date'] = cancellation_date
        items['cancellation_type'] = cancellation_type
        items['manager_name'] = manager_name
        items['unified_credit_code'] = unified_credit_code
        items['registration_location'] = registration_location
        items['office_location'] = office_location
        items['registered_capital'] = registered_capital
        items['Paid_in'] = Paid_in
        items['Enterprise_nature'] = Enterprise_nature
        items['organization_type'] = organization_type
        items['mechanism_website'] = mechanism_website
        items['actual_controller'] = actual_controller
        items['fund_url'] = url
        items['Executive_Information'] = json.dumps(executive_information, ensure_ascii=False)
        items['Related_party_information'] = json.dumps(related_party_information, ensure_ascii=False)
        items['Investor_Information'] = json.dumps(investor_information, ensure_ascii=False)
        items['Product_Information'] = json.dumps(product_information, ensure_ascii=False)
        yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
