"""AMAC 基金公司及子公司集合资管产品 → subsidiary_aggregate_product"""
import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *

_LIST_URL = 'https://gs.amac.org.cn/amac-infodisc/api/fund/account?rand={r}&pageNo={p}&pageSize=20'


class SubsidiarySpider(BaseSpider):
    name = 'amac_subsidiary'
    data_table = 'subsidiary_aggregate_product'
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
            '管理人名称': 'administrator_name',
            '托管人名称': 'custodian_name',
            '备案日期': 'filing_date',
            '成立日期': 'establish_date',
            '到期日': 'due_date',
            '投资类型': 'investment_type',
            '是否分级': 'whether_classification',
            '运作状态': 'operation_status',
        }
        result = {var: '' for var in field_map.values()}
        # 获取标题
        for tr_data in details_tr_list:
            td_title = self.replace_data(tr_data.xpath('./td[1]/text()'))
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
        url = f'https://gs.amac.org.cn/amac-infodisc/api/fund/account?rand={random.random()}&page=0&size=20'
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
            details_url = f'https://gs.amac.org.cn/amac-infodisc/api/fund/account?rand={random.random()}&page={page}&size=20'
            yield scrapy.Request(
                url=details_url,
                method="POST",
                headers=self.headers,
                body=json.dumps({}, separators=(",", ":")),
                callback=self.parse_list,
                dont_filter=True
            )

    def parse_list(self, response):
        response = response.json()
        for data in response['content']:
            details_url = 'https://gs.amac.org.cn/amac-infodisc/res/fund/account/{}.html'.format(data['id'])
            yield scrapy.Request(
                url=details_url,
                method="GET",
                headers=self.headers,
                errback=self.errback,
                callback=self.parse_urls,
                cb_kwargs={'details_url': details_url}
            )

    def parse_urls(self, response, details_url):
        details_lement = etree.HTML(response.body)
        details_tr_list = details_lement.xpath(
            '//div[@class="info-body"]/div[1]/div[@class="table-response"]/table/tbody/tr')
        result = self.parse_item(details_tr_list)
        if result:
            product_name = result['product_name']
            product_code = result['product_code']
            administrator_name = result['administrator_name']
            custodian_name = result['custodian_name']
            establish_date = result['establish_date']
            filing_date = result['filing_date']
            due_date = result['due_date']
            investment_type = result['investment_type']
            whether_classification = result['whether_classification']
            operation_status = result['operation_status']

            # 构建入库字段
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
            items['fund_url'] = details_url
            # insert_data(table='subsidiary_aggregate_product', data=item)
            yield items
        else:
            self.log_error(f'基金公司及子公司集合资管产品数据为空，url：{details_url}')

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
