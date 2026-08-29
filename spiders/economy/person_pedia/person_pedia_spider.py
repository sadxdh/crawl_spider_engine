"""人物百科+员工数量 → personal_character_encyclopedia + entity_staff_number
参照旧项目: data_crawl_server askci_spider.py
来源: s.askci.com
"""
import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *


class PersonPediaSpider(BaseSpider):
    name = 'economy_person_pedia'
    # data_table = 'personal_character_encyclopedia'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;'
                  'q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'referer': 'https://s.askci.com/stock/a-0-0/175/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    }
    stock_list_url = 'https://s.askci.com/stock/0-0-0/{}/'
    detail_url = 'https://s.askci.com/stock/executives/{}/'
    staff_url = 'https://s.askci.com/stock/summary/{}/employee/'

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            url = self.stock_list_url.format(page)
            yield scrapy.Request(
                url=url,
                headers=self.headers,
                callback=self.parse_stock_list
            )

    def parse_stock_list(self, response):
        response = response.text.encode(response.encoding).decode('utf-8')
        result = etree.HTML(response)
        rows = xpath_parse(result, '//table[@id="myTable04"]/tbody/tr', return_list=True)
        for row in rows:
            stock_code = xpath_parse(row, './td[2]/a/text()')
            stock_name = xpath_parse(row, './td[3]/a/text()')
            entity_name = xpath_parse(row, './td[4]/text()')
            temp = {'stock_code': stock_code, 'stock_name': stock_name, 'entity_name': entity_name}
            detail_url = self.detail_url.format(stock_code)
            yield scrapy.Request(
                url=detail_url,
                method="GET",
                headers=self.headers,
                callback=self.parse_detail,
                cb_kwargs={'data': temp}
            )
            staff_url = self.staff_url.format(stock_code)
            yield scrapy.Request(
                url=staff_url,
                method="GET",
                headers=self.headers,
                callback=self.parse_detail,
                cb_kwargs={'data': temp}
            )

    def parse_detail(self, response, data):
        result = etree.HTML(response.text.encode(response.encoding).decode('utf-8'))
        rows = xpath_parse(result, '//div[@class="right_f_d_table mg_tone"]/table/tr[not(@style)]', return_list=True)
        if rows:
            for row in rows:
                res = xpath_parse(row, './td[1]/text()')
                if '序号' in res:
                    continue
                person_name = xpath_parse(row, './td[2]/a/text()')
                appoint_position = xpath_parse(row, './td[3]/text()')
                appoint_date = xpath_parse(row, './td[4]/text()')
                appoint_end_date = xpath_parse(row, './td[5]/text()')
                gender = xpath_parse(row, './td[6]/text()')
                highest_educational = xpath_parse(row, './td[7]/text()')
                birth_date = xpath_parse(row, './td[8]/text()')
                salary = xpath_parse(row, './td[9]/text()')
                hold_stock_num = xpath_parse(row, './td[10]/text()')
                brief_introduction = xpath_parse(row, './td[11]/p/text()')

                stock_code = data['stock_code']
                items = {}
                items['md5_value'] = hash_md5(stock_code + person_name)
                items['stock_code'] = stock_code
                items['stock_name'] = data['stock_name']
                items['person_name'] = person_name
                items['gender'] = gender
                items['birth_date'] = birth_date
                items['highest_educational'] = highest_educational
                items['brief_introduction'] = brief_introduction
                items['appoint_enterprise'] = data['entity_name']
                items['appoint_position'] = appoint_position
                items['appoint_date'] = appoint_date
                items['appoint_end_date'] = appoint_end_date
                items['salary'] = salary
                items['hold_stock_num'] = hold_stock_num
                items['_table'] = 'personal_character_encyclopedia'
                # insert_data(table='personal_character_encyclopedia', data=item)
                yield items

    def parse_staff(self, response, data):
        result = etree.HTML(response.text.encode(response.encoding).decode('utf-8'))
        rows = xpath_parse(result, '//table[@border="1"]/tbody/tr', return_list=True)
        for row in rows:
            staff_category = xpath_parse(row, './td[1]/text()')
            sample_type = '职位' if '人员' in staff_category else '学历'
            if '按专业划分' in staff_category:
                continue
            staff_num = xpath_parse(row, './td[2]/text()')
            staff_ratio = xpath_parse(row, './td[3]/text()')

            stock_code = data['stock_code']
            items = {}
            items['md5_value'] = hash_md5(stock_code + staff_category)
            items['stock_code'] = stock_code
            items['stock_name'] = data['stock_name']
            items['entity_name'] = data['entity_name']
            items['sample_type'] = sample_type
            items['staff_category'] = staff_category
            items['staff_num'] = None if '—' in staff_num else staff_num
            items['staff_ratio'] = None if '—' in staff_ratio else staff_ratio
            items['_table'] = 'entity_staff_number'
            # insert_data(table='entity_staff_number', data=item)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
