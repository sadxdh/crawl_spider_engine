"""AMAC 会员机构 → member_mechanism"""
import hashlib
import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *


_LIST_URL = 'https://gs.amac.org.cn/amac-infodisc/api/pof/pofMember?rand={r}&page={p}&size=20'


class MemberSpider(BaseSpider):
    name = 'amac_member'
    data_table = 'member_mechanism'
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

    def parse_item1(self, details_tr_list):
        field_map = {
            '全称(中文)': 'member_mechanism_name',
            '统一社会信用代码': 'credit_code',
            '组织机构代码': 'credit_code',
            '成立时间': 'establish_time',
            '注册地址': 'register_address',
            '办公地址': 'office_address',
            '注册资本(万元)': 'registered_capital',
            '机构性质': 'mechanism_nature',
            '机构类型': 'mechanism_type',
            '业务类型': 'business_type',
            '员工人数': 'staff_number',
            '机构网址': 'website',
            '当前会员类型': 'member_type',
            '入会时间': 'admission_time',
            '会员代表': 'member_representative',
            '会员编码': 'member_code'
        }
        result = {var: '' for var in field_map.values()}
        # 获取标题
        for tr_data in details_tr_list:
            td_title = self.replace_data(tr_data.xpath('./td[1]/text()'))
            # 遍历字典，匹配标题并设置对应变量
            for title, var_name in field_map.items():
                if title in td_title:
                    text1 = self.replace_data(tr_data.xpath('./td[2]/text()'))
                    text2 = self.replace_data(tr_data.xpath('./td/span/text()'))
                    result[var_name] = text1 if text1 else text2
                    break
        return result

    def parse_item11(self, details_element):
        legal_representative = self.replace_data(details_element.xpath(
            '//div[@class="info-body"]/div[2]/div[@class="table-response"]/table/tbody/tr[1]/td[2]/text()'))
        senior_executive_tr_list = details_element.xpath('//div[@class="info-body"]/div[2]/div[@class="table'
                                                         '-response"]/table/tbody/tr[2]/td[2]/table/tbody/tr')
        senior_executive = []
        for senior_executive_tr in senior_executive_tr_list:
            senior_executive.append(
                {
                    'name': self.replace_data(senior_executive_tr.xpath('./td[1]/text()')),
                    'post': self.replace_data(senior_executive_tr.xpath('./td[2]/text()')),
                    'qualifications': self.replace_data(senior_executive_tr.xpath('./td[2]/text()'))
                }
            )
        senior_executive = json.dumps(senior_executive, ensure_ascii=False)
        return senior_executive, legal_representative

    def replace_data(self, data):
        if data:
            return (data[0].strip().replace('\n', '').replace(u'\xa0', '').replace(" ", "").
                    replace("'", '`').replace('"', '”'))
        else:
            return ''

    def parse_item2(self, response):
        etree_elements = etree.HTML(response.body)
        table1 = etree_elements.xpath(
            '//div[@class="info-body"]/div[@class="section"][1]/div[@class="table-response"]/table/tbody/tr')
        field_map = {
            '基金管理人全称(中文)': 'member_mechanism_name',
            '统一社会信用代码': 'credit_code',
            '组织机构代码': 'credit_code',
            '成立时间': 'establish_time',
            '注册地址': 'register_address',
            '办公地址': 'office_address',
            '注册资本(万元)': 'registered_capital',
            '机构性质': 'mechanism_nature',
            '企业性质': 'mechanism_nature',
            '机构类型': 'mechanism_type',
            '业务类型': 'business_type',
            '员工人数': 'staff_number',
            '机构网址': 'website',
            '当前会员类型': 'member_type',
            '入会时间': 'admission_time',
            '会员代表': 'member_representative',
            '会员编码': 'member_code',
        }
        result = {var: '' for var in field_map.values()}
        # 获取标题
        for tr_data in table1:
            td_title = self.replace_data(tr_data.xpath('./td[1]/text()'))
            if not td_title:
                td_title = self.replace_data(tr_data.xpath('./td[1]/div/text()'))
            # 遍历字典，匹配标题并设置对应变量
            for title, var_name in field_map.items():
                if title in td_title:
                    text1 = self.replace_data(tr_data.xpath('./td[2]/text()'))
                    text2 = self.replace_data(tr_data.xpath('./td/span/text()'))
                    result[var_name] = text1 if text1 else text2
                    break
        table2 = etree_elements.xpath(
            '//div[@class="info-body"]/div[@class="section"][2]/div[@class="table-response"]/table/tbody/tr')
        for tr in table2:
            tds = tr.xpath('./td')
            if len(tds) > 1 and tds[0].text.strip() == '当前会员类型':
                result['member_type'] = tds[1].text
            if len(tds) > 3 and tds[2].text.strip() == '入会时间':
                result['admission_time'] = tds[3].text
            if len(tds) > 3 and tds[2].text.strip() == '会员代表':
                result['member_representative'] = tds[3].text
        table3 = etree_elements.xpath(
            '//div[@class="info-body"]/div[@class="section"][5]/div[@class="table-response"]/table/tbody/tr')
        senior_executive = []
        legal_representative = ''
        for tr in table3:
            name, post = '', ''
            tds = tr.xpath('./td')
            if len(tds) > 1 and tds[0].text.strip() == '职务':
                post = tds[1].text.strip()
                if '法定代表人' in post:
                    legal_representative = tds[3].text.strip()
            if len(tds) > 3 and tds[2].text.strip() == '姓名':
                name = tds[3].text.strip()
            if post and name:
                senior_executive.append(
                    {
                        'name': name,
                        'post': post,
                        'qualifications': post
                    }
                )
        if not senior_executive and legal_representative:
            senior_executive.append(
                {
                    'name': legal_representative,
                    'post': '法定代表人',
                    'qualifications': '法定代表人'
                }
            )
        senior_executive = json.dumps(senior_executive, ensure_ascii=False)
        return result, senior_executive, legal_representative


    def start_requests(self):
        url = f'https://gs.amac.org.cn/amac-infodisc/api/pof/pofMember?rand={random.random()}&page=0&size=20'
        yield scrapy.Request(
            url=url,
            method="POST",
            headers=self.headers,
            body=json.dumps({}, separators=(",", ":")),
            callback=self.parse_total_pages,
            dont_filter=True,
        )

    def parse_total_pages(self, response):
        count_page = response.json()['totalPages']
        if int(self.end_page) < 0:
            pages = [page for page in range(int(self.start_page) - 1, int(count_page))]
        else:
            pages = [page for page in range(int(count_page) - 1, int(count_page) - int(self.end_page) - 1, -1)]
        for page in pages:
            details_url = f'https://gs.amac.org.cn/amac-infodisc/api/pof/pofMember?rand={random.random()}&page={page}&size=20'
            yield scrapy.Request(
                url=details_url,
                method="POST",
                headers=self.headers,
                body=json.dumps({}, separators=(",", ":")),
                callback=self.parse_urls,
                dont_filter=True,
                cb_kwargs={'details_url': details_url}
            )

    def parse_urls(self, response, details_url):
        for content in reversed(response.json()['content']):
            user_tenant_id = content['userTenantId']
            details_url1 = f'https://gs.amac.org.cn/amac-infodisc/res/pof/member/{user_tenant_id}.html'
            details_url2 = f'https://gs.amac.org.cn/amac-infodisc/res/pof/manager/{user_tenant_id}.html'
            yield scrapy.Request(
                url=details_url1,
                headers=self.headers,
                method="GET",
                callback=self.parse_detail1,
                dont_filter=True,
                cb_kwargs={'details_url1': details_url1, 'details_url2': details_url2}
            )

    def parse_detail1(self, response, details_url1, details_url2):
        try:
            details_element = etree.HTML(response.body)
            details_tr_list = details_element.xpath(
                '//div[@class="info-body"]/div[@class="section"][1]/div[@class="table-response"]/table/tbody/tr')
            result = self.parse_item1(details_tr_list)
            senior_executive, legal_representative = self.parse_item11(details_element)
            data_data = self.insert_data(result, senior_executive, legal_representative, details_url1)
            yield data_data
        except:
            yield scrapy.Request(
                url=details_url2,
                headers=self.headers,
                method="GET",
                callback=self.parse_detail2,
                dont_filter=True,
                cb_kwargs={'details_url1': details_url1, 'details_url2': details_url2}
            )

    def parse_detail2(self, response, details_url1, details_url2):
        try:
            result, senior_executive, legal_representative = self.parse_item2(response)
            data_data = self.insert_data(result, senior_executive, legal_representative, details_url2)
            yield data_data
        except Exception as e:
            self.log_info(f"manager错误url：{details_url2},{e}")


    def insert_data(self, result, senior_executive, legal_representative, details_url):
        member_mechanism_name = result['member_mechanism_name']
        credit_code = result['credit_code']
        establish_time = result['establish_time']
        register_address = result['register_address']
        office_address = result['office_address']
        registered_capital = result['registered_capital']
        mechanism_nature = result['mechanism_nature']
        staff_number = result['staff_number']
        member_type = result['member_type']
        admission_time = result['admission_time']
        member_representative = result['member_representative']
        mechanism_type = result['mechanism_type']
        business_type = result['business_type']
        website = result['website']
        member_code = result['member_code']

        # 构建入库字段
        md5_value = hash_md5(member_mechanism_name + credit_code)
        items = {}
        items['md5_value'] = md5_value
        items['member_mechanism_name'] = member_mechanism_name
        items['Credit_code'] = credit_code
        items['establish_time'] = establish_time
        items['register_address'] = register_address
        items['office_address'] = office_address
        items['registered_capital'] = registered_capital
        items['mechanism_nature'] = mechanism_nature
        items['staff_number'] = staff_number
        items['member_type'] = member_type
        items['admission_time'] = admission_time
        items['member_representative'] = member_representative
        items['member_code'] = member_code
        items['Legal_representative'] = legal_representative
        items['senior_executive'] = senior_executive
        items['mechanism_type'] = mechanism_type
        items['business_type'] = business_type
        items['website'] = website
        items['url'] = details_url
        return items


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
