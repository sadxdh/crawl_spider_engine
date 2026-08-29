import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class IndustryStandardSpider(BaseSpider):
    name = 'entity_industry_standard'
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
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://hbba.sacinfo.org.cn',
        'referer': 'https://hbba.sacinfo.org.cn/stdList',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    }
    base_url = 'https://hbba.sacinfo.org.cn/stdQueryList'
    detail_url = 'https://hbba.sacinfo.org.cn/stdDetail/{}'

    @staticmethod
    def generate_data(page):
        data = {
            'current': str(page),
            'size': '100',
            'key': '',
            'ministry': '',
            'industry': '',
            'pubdate': '',
            'date': '',
            'status': '',
        }
        return data

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            data = self.generate_data(page)
            yield scrapy.FormRequest(
                url=self.base_url,
                method='POST',
                headers=self.headers,
                formdata=data,
                callback=self.parse_list,
                dont_filter=True,
            )

    def parse_list(self, response):
        rows = response.json()['records']
        for row in rows:
            publish_date = timestamp_to_datetime(row['issueDate']) if row.get('issueDate') else None
            implement_date = timestamp_to_datetime(row['actDate']) if row.get('actDate') else None
            standard_num = row['code']
            standard_name = row['chName']
            standard_status = row['status']
            detail_id = row['pk']

            temp = {'publish_date': publish_date, 'implement_date': implement_date, 'standard_num': standard_num,
                    'standard_name': standard_name, 'standard_status': standard_status, 'detail_id': detail_id}

            detail_url = self.detail_url.format(detail_id)
            yield scrapy.Request(
                url=detail_url,
                method='GET',
                headers=self.headers,
                callback=self.get_detail,
                cb_kwargs={'data': temp}
            )

    def get_detail(self, response, data):
        temp = self.parse_detail(response)
        data.update(temp)
        yield from self.save_data(data)

    @staticmethod
    def parse_detail(response):
        result = etree.HTML(response.text)
        # 基础信息
        dt_list = result.xpath('//dl/dt/text()')
        dd_list = result.xpath('//dl/dd/text()')
        dd_list = [i.strip() for i in dd_list]
        dd_dict = dict(zip(dt_list, dd_list))

        abolish_date = dd_dict.get('废止日期')
        make_revisions = dd_dict.get('制修订')
        replace_standard = dd_dict.get('代替标准')
        china_standard_class_num = dd_dict.get('中国标准分类号')
        international_standard_class_num = dd_dict.get('国际标准分类号')
        technical_committees = dd_dict.get('技术归口')
        approve_publish_department = dd_dict.get('批准发布部门')
        industry_class = dd_dict.get('行业分类')
        standard_class = dd_dict.get('标准类别')

        record_num = xpath_parse(result, '//p[contains(text(),"备案号")]/text()')
        record_num = record_num.split('：')[1] if record_num else None
        record_date = xpath_parse(result, '//p[contains(text(),"备案日期")]/text()')
        record_date = record_date.split('：')[1] if record_date else None

        # 起草单位
        xpath_content = '//h2[text()="起草单位"]/../following-sibling::p[1]/text()'
        drafting_unit = xpath_parse(result, xpath_content, placeholder=',')
        if not drafting_unit:
            xpath_content = '//h2[text()="起草单位"]/../following-sibling::div[1]/dl/dd/a/text()'
            drafting_unit = xpath_parse(result, xpath_content, placeholder=',')
        # 起草人
        drafter_xpath_content = '//h2[text()="起草人"]/../following-sibling::p[1]/text()'
        drafter = xpath_parse(result, drafter_xpath_content, placeholder=',')
        if not drafter:
            drafter_xpath_content = '//h2[text()="起草人"]/../following-sibling::div[1]/dl/dd/a/text()'
            drafter = xpath_parse(result, drafter_xpath_content, placeholder=',')

        temp = {
            'abolish_date': abolish_date,
            'make_revisions': make_revisions,
            'replace_standard': replace_standard,
            'china_standard_class_num': china_standard_class_num,
            'international_standard_class_num': international_standard_class_num,
            'technical_committees': technical_committees,
            'approve_publish_department': approve_publish_department,
            'industry_class': industry_class,
            'standard_class': standard_class,
            'record_num': record_num,
            'record_date': record_date,
            'drafting_unit': drafting_unit,
            'drafter': drafter
        }
        return temp

    def save_data(self, data):
        items = {}
        items['standard_name'] = data['standard_name']
        items['standard_num'] = data['standard_num']
        items['standard_level'] = '行业标准'
        items['standard_status'] = data['standard_status']
        items['standard_class'] = data.get('standard_class')

        items['publish_date'] = data['publish_date']
        items['implement_date'] = data['implement_date']
        items['abolish_date'] = data.get('abolish_date')
        items['competent_department'] = data.get('competent_department')
        items['technical_committees'] = data.get('technical_committees')

        items['make_revisions'] = data.get('make_revisions')
        items['replace_standard'] = data.get('replace_standard')
        items['industry_class'] = data.get('industry_class')
        items['approve_publish_department'] = data.get('approve_publish_department')
        items['china_standard_class_num'] = data.get('china_standard_class_num')
        items['international_standard_class_num'] = data.get('international_standard_class_num')
        items['national_economy_class'] = data.get('national_economy_class')

        items['record_num'] = data.get('record_num')
        items['record_date'] = data.get('record_date')
        items['drafting_unit'] = data.get('drafting_unit')
        items['drafter'] = data.get('drafter')
        items['md5_value'] = hash_md5(data['standard_num'] + data['standard_status'])
        # insert_data(table='entity_standard_info', data=item)
        yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')