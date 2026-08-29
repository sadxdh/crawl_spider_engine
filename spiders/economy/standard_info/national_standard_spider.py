import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class NationalStandardSpider(BaseSpider):
    name = 'entity_national_standard'
    data_table = 'entity_standard_info'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': 'https://std.samr.gov.cn/gb/gbQuery',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    }
    base_url = 'https://std.samr.gov.cn/gb/search/gbQueryPage'
    detail_url = 'https://std.samr.gov.cn/gb/search/gbDetailed'

    @staticmethod
    def generate_params(page):
        params = {
            'searchText': '',
            'ics': '',
            'state': '',
            'ISSUE_DATE': '',
            'sortOrder': 'asc',
            'pageSize': '100',
            'pageNumber': page,
        }
        return params

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            params = self.generate_params(page)
            separator = '&' if '?' in self.base_url else '?'
            request_url = f'{self.base_url}{separator}{urlencode(params)}'

            yield scrapy.Request(
                url=request_url,
                method='GET',
                headers=self.headers,
                callback=self.parse_list,
                dont_filter=True,
            )

    def parse_list(self, response):
        result = response.json()
        rows = result.get('rows')
        for row in rows:
            publish_date = row['ISSUE_DATE']
            implement_date = row['ACT_DATE']
            standard_num = row['C_STD_CODE']
            standard_name = row['C_C_NAME']
            standard_status = row['STATE']
            standard_nature = row['STD_NATURE']
            detail_id = row['id']

            temp = {'publish_date': publish_date, 'implement_date': implement_date, 'standard_num': standard_num,
                    'standard_name': standard_name, 'standard_status': standard_status,
                    'standard_nature': standard_nature, 'detail_id': detail_id}
            params = {'id': detail_id}
            separator = '&' if '?' in self.detail_url else '?'
            request_url = f'{self.detail_url}{separator}{urlencode(params)}'

            yield scrapy.Request(
                url=request_url,
                method='GET',
                headers=self.headers,
                callback=self.get_detail,
                dont_filter=True,
                cb_kwargs={'data': temp},
            )

    def get_detail(self, response, data):
        temp = self.parse_detail(response)
        data.update(temp)
        yield from self.save_data(data)

    @staticmethod
    def parse_detail(response):
        result = etree.HTML(response.text)
        standard_en_name = xpath_parse(result, '//div[@class="page-header"]/h5/text()')
        standard_level = xpath_parse(result, '//span[contains(@class,"label-info")]/text()')
        # 基础信息
        base_info = xpath_parse(result, '//h2[text()="基础信息"]/../following-sibling::div[1]')
        column_name = base_info.xpath('./dl[1]/dt/text()')
        column_value = base_info.xpath('./dl[1]/dd/text()')
        column_dict = dict(zip(column_name, column_value))
        abolish_date = column_dict.get('废止日期')
        replace_standard = column_dict.get('代替标准')

        standard_class = xpath_parse(base_info, './dl[2]/dd[1]/text()')
        china_standard_class_num = xpath_parse(base_info, './dl[2]/dd[2]/text()')
        international_standard_class_num = xpath_parse(base_info, './dl[2]/dd/div/table//tr[2]/td/text()')
        competent_department = xpath_parse(base_info, './dl[2]/dd/a[@cd_code="1"]/text()')
        technical_committees = xpath_parse(base_info, './dl[2]/dd/a[@ta_code="1"]/text()')
        # 起草单位
        xpath_content = '//h2[text()="起草单位"]/../following-sibling::div[1]/dl/dd/a/text()'
        drafting_unit = xpath_parse(result, xpath_content, placeholder=',')
        # 起草人
        drafter_xpath_content = '//h2[text()="起草人"]/../following-sibling::div[1]/dl/dd/a/text()'
        drafter = xpath_parse(result, drafter_xpath_content, placeholder=',')

        temp = {
            'standard_en_name': standard_en_name,
            'standard_level': standard_level,
            'standard_class': standard_class,
            'abolish_date': abolish_date,
            'replace_standard': replace_standard,
            'competent_department': competent_department,
            'technical_committees': technical_committees,
            'china_standard_class_num': china_standard_class_num,
            'international_standard_class_num': international_standard_class_num,
            'drafting_unit': drafting_unit,
            'drafter': drafter
        }
        return temp

    def save_data(self, data):
        items = {}
        items['standard_name'] = data['standard_name']
        items['standard_en_name'] = data.get('standard_en_name')
        items['standard_num'] = data['standard_num']
        items['standard_level'] = data['standard_level']
        items['standard_status'] = data['standard_status']
        items['standard_class'] = data.get('standard_class')
        items['standard_nature'] = data['standard_nature']
        items['publish_date'] = data['publish_date']
        items['implement_date'] = data['implement_date']
        items['abolish_date'] = data.get('abolish_date')

        items['competent_department'] = data.get('competent_department')
        items['technical_committees'] = data.get('technical_committees')
        items['china_standard_class_num'] = data.get('china_standard_class_num')
        items['international_standard_class_num'] = data.get('international_standard_class_num')
        items['national_economy_class'] = data.get('national_economy_class')
        items['replace_standard'] = data.get('replace_standard')

        items['drafting_unit'] = data.get('drafting_unit')
        items['drafter'] = data.get('drafter')
        items['md5_value'] = hash_md5(data['standard_num'] + data['standard_status'])
        # insert_data(table='entity_standard_info', data=item)
        yield items

def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')