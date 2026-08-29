import hashlib, scrapy
from typing import Any
from urllib.parse import urlencode

from pdfkit import source
from scrapy.http import Response

from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class AmacPrivateFundManagerProductSpider(BaseSpider):
    name = 'amac_private_fund_manager_product'
    data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 4, 'DOWNLOAD_DELAY': 0.5,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        },
        'RETRY_ENABLED': True,
        "RETRY_HTTP_CODES": [566],
        "RETRY_TIMES": 3,  # 失败重试
        #'COOKIES_ENABLED': True  # 使用cookie字段必须得要
    }
    proxy_type = 'long_proxy'

    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Origin": "https://gs.amac.org.cn",
        "Referer": "https://gs.amac.org.cn/amac-infodisc/res/pof/member/index.html",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": "\"Not;A=Brand\";v=\"8\", \"Chromium\";v=\"150\", \"Google Chrome\";v=\"150\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    institution_info = {
        # member 机构信息字段
        '会员机构全称(中文)': "institution_name",
        '会员机构全称（中文）': "institution_name",
        '会员机构全称(英文)': "institution_name_en",
        '会员机构全称（英文）': "institution_name_en",
        '统一社会信用代码/组织机构代码': "Credit_code",
        '统一社会信息代码/组织机构代码': "Credit_code",
        # manager 机构信息字段
        '基金管理人全称(中文)': "institution_name",
        '基金管理人全称（中文）': "institution_name",
        '基金管理人全称(英文)': "institution_name_en",
        '基金管理人全称（英文）': "institution_name_en",
        '组织机构代码': "Credit_code",
    }


    product_info = {
        '产品名称': "product_name",
        '产品编码': "product_code",
        '管理人名称': "administrator_name",
        '备案日期': "filing_date",
        '成立日期': "establish_date",
        '到期日': "due_date",
        '投资类型': "investment_type",
        '是否分级': "whether_classification",
        '运作状态': "operation_status",
        '是否托管': "is_hosting",
        '托管人名称': "custodian_name",
        '基金类型': "investment_type",
        '组织形式': "organizational_form",
        '基金名称': "product_name",
        '基金编号': "product_code",
        '成立时间': "establish_date",
        '备案时间': "filing_date",
        '注册地': "registration_address",
        '基金备案阶段': "fund_registration_stage",
        '币种': "currency",
        '基金管理人名称': "administrator_name",
        '管理类型': "administration_type",
        '基金信息最后更新时间': "last_updatetime",
    }

    def start_requests(self):
        url ="https://gs.amac.org.cn/amac-infodisc/api/pof/pofMember?rand=&page=0&size=20"
        yield scrapy.Request(
            url=url,
            method="POST",
            headers=self.headers,
            body=json.dumps({}).encode("utf-8"),
            callback=self.get_total_pages,
            dont_filter=True
        )

    def get_total_pages(self, response):
        if self.end_page < 1:
            totalpages = response.json().get('totalPages')
        else:
            totalpages = self.end_page
        if totalpages:
            for page in range(self.start_page - 1, totalpages):
                url = f"https://gs.amac.org.cn/amac-infodisc/api/pof/manager/query?&page={page}&size=20"
                yield scrapy.Request(
                    url=url,
                    method="POST",
                    headers=self.headers,
                    body=json.dumps({}).encode("utf-8"),
                    callback=self.parse_list,
                    dont_filter=True
                )

    def parse_list(self, response):
        for data_list in response.json().get('content', []):
            detail_url = f"https://gs.amac.org.cn/amac-infodisc/res/pof/manager/{data_list['url']}"
            yield scrapy.Request(
                url=detail_url,
                method="GET",
                headers=self.headers,
                callback=self.parse_manager_detail,
                cb_kwargs={'detail_url': detail_url}
            )

    # manager产品数据提取
    def parse_manager_detail(self, response, detail_url):
        manager_info = {}
        soup = BeautifulSoup(response.text, 'lxml')
        for title_list in soup.select('.info-body>.section'):
            # 机构信息
            if title_list.select('.common-tit')[0].text.strip() == '机构信息':
                for tr_list in title_list.select('.table-response>table>tbody>tr'):
                    if len(tr_list.select('td')) >= 2:
                        key = self.clean_text(tr_list.select('td')[0].text.strip())
                        if tr_list.select('#complaint2'):
                            value = self.clean_text(tr_list.select('#complaint2')[0].text.strip())
                        else:
                            value = self.clean_text(tr_list.select('td')[1].text.strip())
                        key_name = self.institution_info.get(key)
                        if key_name:
                            manager_info[key_name] = value
            # 产品信息
            if title_list.select('.common-tit')[0].text.strip() == '产品信息':
                Product_Information = []
                for tr_data in title_list.select('.table-response>table>tbody>tr a'):
                    product_url = urljoin(detail_url, tr_data['href'])
                    Product_Information.append(product_url)
                manager_info['Product_Information'] = Product_Information
        manager_info['detail_url'] = detail_url
        yield from self.parse_manager_products(manager_info)

    def parse_manager_products(self, manager_info):
        institution_name = manager_info.get('institution_name')
        Credit_code = manager_info.get('Credit_code')
        if manager_info.get('Product_Information'):
            for product_url in manager_info['Product_Information']:
                yield scrapy.Request(
                    url=product_url,
                    method="GET",
                    headers=self.headers,
                    callback=self.parse_fund_son_products,
                    cb_kwargs={'institution_name': institution_name, 'Credit_code': Credit_code, 'product_url': product_url}
                )

    def get_manager_table(self, title_list):
        data_data = {}
        for tr_data in title_list.select('.table-response>table>tbody>tr'):
            key_name = self.clean_text(tr_data.select('td')[0].text.strip())
            key_value = self.clean_text(tr_data.select('td')[1].text.strip())
            data_data[key_name] = key_value
        return data_data


    def parse_fund_son_products(self, response, institution_name, Credit_code, product_url):
        soup = BeautifulSoup(response.text, 'lxml')
        product_data = {}
        product_data['institution_name'] = institution_name
        product_data['Credit_code'] = Credit_code
        product_data['product_url'] = product_url
        for tr_list in soup.select('.info-body>.section')[0].select('.table-response>table>tbody>tr'):
            key_name = tr_list.select('td')[0].text.strip().replace(':', '')
            if self.product_info.get(key_name):
                product_data[self.product_info[key_name]] = self.clean_text(tr_list.select('td')[1].text.strip())
        for title_list in soup.select('.info-body>.section'):
            if title_list.select('.common-tit') and title_list.select('.common-tit')[0].text.strip() == '信息披露情况':
                product_data['information_disclosure'] = self.get_manager_table(title_list)
        yield from self.data_insert(product_data)


    def data_insert(self, data_data):
        institution_name = data_data.get('institution_name')  # 机构全称(中文)
        Credit_code = data_data.get('Credit_code')  # 统一社会信用代码/组织机构代码
        # 以下是产品数据
        product_name = data_data.get('product_name') # 产品名称
        product_code = data_data.get('product_code') # 产品编码
        administrator_name = data_data.get('administrator_name') # 管理人名称
        filing_date = data_data.get('filing_date') # 备案日期
        establish_date = data_data.get('establish_date') # 成立日期
        due_date = data_data.get('due_date') # 到期日
        investment_type = data_data.get('investment_type') # 投资类型/基金类型
        whether_classification = data_data.get('whether_classification') # 是否分级
        operation_status = data_data.get('operation_status') # 运作状态
        is_hosting = data_data.get('is_hosting') # 是否托管
        custodian_name = data_data.get('custodian_name') # 托管人名称
        organizational_form = data_data.get('organizational_form') # 组织形式
        registration_address = data_data.get('registration_address') # 注册地
        fund_registration_stage = data_data.get('fund_registration_stage') # 基金备案阶段
        currency = data_data.get('currency') # 币种
        administration_type = data_data.get('administration_type') # 管理类型
        last_updatetime = data_data.get('last_updatetime') # 基金信息最后更新时间
        information_disclosure = data_data.get('information_disclosure') # 信息披露情况
        source = data_data.get('product_url')   #来源链接

        # 根据组织机构代码判断，如果长度为18为则由这个值生成md5，否则用名称
        # 这是管理人的id
        if Credit_code and len(Credit_code) == 18:
            administrator_md5 = hash_md5(Credit_code)   # 管理人的MD5
        else:
            administrator_md5 = hash_md5(institution_name)  # 管理人的MD5
        md5_value = hash_md5(f"{product_name}{administrator_name}")

        main_item = {}
        main_item['product_name'] = product_name
        main_item['product_code'] = product_code
        main_item['administrator_name'] = administrator_name
        main_item['filing_date'] = filing_date
        main_item['establish_date'] = establish_date
        main_item['due_date'] = due_date
        main_item['investment_type'] = investment_type
        main_item['whether_classification'] = whether_classification
        main_item['operation_status'] = operation_status
        main_item['is_hosting'] = is_hosting
        main_item['custodian_name'] = custodian_name
        main_item['organizational_form'] = organizational_form
        main_item['registration_address'] = registration_address
        main_item['fund_registration_stage'] = fund_registration_stage
        main_item['currency'] = currency
        main_item['administration_type'] = administration_type
        main_item['last_updatetime'] = last_updatetime
        main_item['information_disclosure'] = json.dumps(information_disclosure, ensure_ascii=False) if information_disclosure else None
        main_item['administrator_md5'] = administrator_md5
        main_item['source'] = source
        main_item['md5_value'] = md5_value
        main_item['_table'] = 'private_equity_fund_products'

        yield main_item


    def clean_text(self, text):
        return ' '.join(text.split()) if text else ''


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')