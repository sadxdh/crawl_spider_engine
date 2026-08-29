import hashlib, scrapy
from urllib.parse import urlencode

from pdfkit import source

from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

# 私募基金管理人分类查询公示
class AmacPrivateFundManagerSpider(BaseSpider):
    name = 'amac_private_fund_manager'
    data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 5, 'DOWNLOAD_DELAY': 0.5,
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
        '成立时间': "establish_time",
        '注册地址': "register_address",
        '办公地址': "office_address",
        '注册资本(万元)(人民币)': "registered_capital",
        '机构性质': "mechanism_nature",
        '机构类型': "mechanism_type",
        '业务类型': "business_type",
        '员工人数': "staff_number",
        '机构网址': "website",
        '当前会员类型': "member_type",
        '入会时间': "admission_time",
        '会员机构代表': "member_representative",
        # manager 机构信息字段
        '基金管理人全称(中文)': "institution_name",
        '基金管理人全称（中文）': "institution_name",
        '基金管理人全称(英文)': "institution_name_en",
        '基金管理人全称（英文）': "institution_name_en",
        '登记编号': "registration_number",
        '组织机构代码': "Credit_code",
        '登记时间': "registration_date",
        '实缴资本(万元)(人民币)': "Paid_in",
        '注册资本实缴比例': "Registration_ratio",
        '企业性质': "mechanism_nature",
        '全职员工人数': "Full_time_staff",
        '取得基金从业人数': "Number_of_Fund_Members",
        '是否为符合提供投资建议条件的第三方机构': "is_investment_organization",
        '管理规模区间': "fund_size",
        '机构信息最后更新时间': "Institutional_update_time",
    }

    table_key_en = {
        '时间': "employing_time",
        "任职单位": 'employing_organization',
        '任职部门': 'employing_department',
        '职务': 'post',
        '序号': 'num',
        '姓名': 'name',
        '类型': 'type',
        '名称': 'name',
        '登记编号': 'registration_number',
        '组织机构代码': 'code',
        '姓名/名称': 'name',
        '认缴比例': 'contribution_ratio',
        '月报': 'monthly_report',
        '季报': 'quarterly_report',
        '半年报': 'interim_report',
        '年报': 'annual_report',
        '投资者查询账号开立率': 'ratio',
        '高管姓名': 'name',
        '是否具有基金从业资格': 'is_qualifications',
        '产品类型': 'product_type',
        '产品数量': 'product_number',
    }



    def start_requests(self):
        url ="https://gs.amac.org.cn/amac-infodisc/api/pof/manager/query?&page=0&size=20"
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
                cb_kwargs={'detail_url': detail_url, 'data_list': data_list}
            )

    def parse_manager_detail(self, response, detail_url, data_list):
        manager_info = {}
        soup = BeautifulSoup(response.text, 'lxml')
        manager_info['manager_has_product'] = "是" if data_list.get('managerHasProduct') else "否"  # 是否为理、监事单位
        manager_info['primary_invest_type'] = data_list.get('primaryInvestType')  # 机构类型
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
            # 会员信息
            if title_list.select('.common-tit')[0].text.strip() in ['会员信息', '机构信息']:
                td_list = title_list.select('.table-response>table>tbody>tr>td')
                for td_num in range(len(td_list)):
                    if td_list[td_num].get('class') == ['title']:
                        if td_list[td_num].text.strip() == '会员机构代表':
                            manager_info['member_representative'] = self.clean_text(td_list[td_num + 1].text.strip())
                        if td_list[td_num].text.strip() == '当前会员类型':
                            manager_info['member_type'] = self.clean_text(td_list[td_num + 1].text.strip())
                        if td_list[td_num].text.strip() == '入会时间':
                            manager_info['admission_time'] = self.clean_text(td_list[td_num + 1].text.strip())
                        if td_list[td_num].text.strip() == '是否为会员':
                            manager_info['is_member'] = self.clean_text(td_list[td_num + 1].text.strip())
            # 法律意见书信息
            if title_list.select('.common-tit')[0].text.strip() == '法律意见书信息':
                manager_info['legal_opinion_information'] = self.get_manager_legal_opinion_information(title_list)
            # 实际控制人信息
            if title_list.select('.common-tit')[0].text.strip() == '实际控制人信息':
                manager_info['actual_controller_information'] = self.get_manager_table(title_list)
            # 高管信息
            if title_list.select('.common-tit')[0].text.strip() == '高管信息':
                manager_info['senior_executive'] = self.get_manager_senior_executive(title_list)
            # 董事、监事信息
            if title_list.select('.common-tit')[0].text.strip() == '董事、监事信息':
                manager_info['directors_supervisors'] = self.get_manager_directors_supervisors(title_list)
            # 关联方信息（仅包含关联私募基金管理人）
            if title_list.select('.common-tit')[0].text.strip() == '关联方信息（仅包含关联私募基金管理人）':
                manager_info['Related_party_information'] = self.get_manager_table(title_list)
            # 出资人信息
            if title_list.select('.common-tit')[0].text.strip() == '出资人信息':
                manager_info['Investor_Information'] = self.get_manager_table(title_list)
            # 产品信息
            if title_list.select('.common-tit')[0].text.strip() == '产品信息':
                manager_info['Product_Information'] = self.get_manager_table(title_list)

        manager_info['detail_url'] = detail_url
        yield from self.data_insert(manager_info)


    def data_insert(self, data_data):
        institution_name = data_data.get('institution_name')  # 机构全称(中文)
        institution_name_en = data_data.get('institution_name_en')  # 机构全称(英文)
        manager_has_product = data_data.get('manager_has_product')    # 是否存在正在管理的私募基金
        primary_invest_type = data_data.get('primary_invest_type')  # 机构类型
        registration_number = data_data.get('registration_number')  # 登记编号
        Credit_code = data_data.get('Credit_code')  # 统一社会信用代码/组织机构代码
        registration_date = data_data.get('registration_date')  # 登记时间
        establish_time = data_data.get('establish_time')  # 成立时间
        register_address = data_data.get('register_address')  # 注册地址
        office_address = data_data.get('office_address')  # 办公地址
        registered_capital = data_data.get('registered_capital')  # 注册资本(万元)(人民币)
        Paid_in = data_data.get('Paid_in')  # 实缴资本(万元)(人民币)
        Registration_ratio = data_data.get('Registration_ratio')  # 注册资本实缴比例
        mechanism_nature = data_data.get('mechanism_nature')  # 机构性质
        mechanism_type = data_data.get('mechanism_type')  # 机构类型
        business_type = data_data.get('business_type')  # 业务类型
        staff_number = data_data.get('staff_number')  # 员工人数
        website = data_data.get('website')  # 机构网址
        Full_time_staff = data_data.get('Full_time_staff')  # 全职员工人数
        Number_of_Fund_Members = data_data.get('Number_of_Fund_Members')  # 取得基金从业人数
        is_investment_organization = data_data.get('is_investment_organization')  # 是否为符合提供投资建议条件的第三方机构
        fund_size = data_data.get('fund_size')  # 管理规模区间
        Institutional_update_time = data_data.get('Institutional_update_time')  # 机构信息最后更新时间
        is_member = data_data.get('is_member')  # 是否会员
        member_type = data_data.get('member_type')  # 当前会员类型
        admission_time = data_data.get('admission_time')  # 入会时间
        member_representative = data_data.get('member_representative')  # 会员机构代表
        senior_executive = data_data.get('senior_executive')    # 会员机构高管/主要负责人/主要合伙人信息
        legal_opinion_information = data_data.get('legal_opinion_information') # 法律意见书信息
        actual_controller_information = data_data.get('actual_controller_information') # 实际控制人信息
        directors_supervisors = data_data.get('directors_supervisors') # 董事、监事信息
        Related_party_information = data_data.get('Related_party_information') # 关联方信息（仅包含关联私募基金管理人）
        Investor_Information = data_data.get('Investor_Information') # 出资人信息
        Product_Information = data_data.get('Product_Information') # 产品信息
        source = data_data.get('detail_url') # 来源链接

        # 根据组织机构代码判断，如果长度为18为则由这个值生成md5，否则用名称
        if Credit_code and len(Credit_code) == 18:
            md5_value = hash_md5(Credit_code)
        else:
            md5_value = hash_md5(institution_name)


        main_item = {}
        main_item['institution_name'] = institution_name
        main_item['institution_name_en'] = institution_name_en
        main_item['manager_has_product'] = manager_has_product
        main_item['primary_invest_type'] = primary_invest_type
        main_item['registration_number'] = registration_number
        main_item['Credit_code'] = Credit_code
        main_item['registration_date'] = registration_date
        main_item['establish_time'] = establish_time
        main_item['register_address'] = register_address
        main_item['office_address'] = office_address
        main_item['registered_capital'] = registered_capital
        main_item['Paid_in'] = Paid_in
        main_item['Registration_ratio'] = Registration_ratio
        main_item['mechanism_nature'] = mechanism_nature
        main_item['mechanism_type'] = mechanism_type
        main_item['business_type'] = business_type
        main_item['staff_number'] = staff_number
        main_item['website'] = website
        main_item['Full_time_staff'] = Full_time_staff
        main_item['Number_of_Fund_Members'] = Number_of_Fund_Members
        main_item['is_investment_organization'] = is_investment_organization
        main_item['fund_size'] = fund_size
        main_item['Institutional_update_time'] = Institutional_update_time
        main_item['is_member'] = is_member
        main_item['member_type'] = member_type
        main_item['admission_time'] = admission_time
        main_item['member_representative'] = member_representative
        main_item['senior_executive'] = json.dumps(senior_executive, ensure_ascii=False) if senior_executive else None
        main_item['legal_opinion_information'] = json.dumps(legal_opinion_information, ensure_ascii=False) if legal_opinion_information else None
        main_item['actual_controller_information'] = json.dumps(actual_controller_information, ensure_ascii=False) if actual_controller_information else None
        main_item['directors_supervisors'] = json.dumps(directors_supervisors, ensure_ascii=False) if directors_supervisors else None
        main_item['Related_party_information'] = json.dumps(Related_party_information, ensure_ascii=False) if Related_party_information else None
        main_item['Investor_Information'] = json.dumps(Investor_Information, ensure_ascii=False) if Investor_Information else None
        main_item['Product_Information'] = json.dumps(Product_Information, ensure_ascii=False) if Product_Information else None
        main_item['source'] = source
        main_item['md5_value'] = md5_value
        main_item['_table'] = 'private_fund_manager_info'

        yield main_item

    def get_manager_table(self, title_list):
        data_data = {}
        for tr_data in title_list.select('.table-response>table>tbody>tr'):
            key_name = self.clean_text(tr_data.select('td')[0].text.strip())
            table = tr_data.select('td')[1].find("table", recursive=False)
            if table:
                # 获取表头
                table_head = []
                for head in tr_data.select('td')[1].select('thead>tr>th'):
                    table_head.append(self.table_key_en[self.clean_text(head.text.strip())])
                # 获取表数据
                key_value = []
                for value in tr_data.select('td')[1].select('tbody>tr'):
                    value_data = {}
                    td_value_data = value.select('td')
                    for td_num in range(len(td_value_data)):
                        value_data[table_head[td_num]] = self.clean_text(td_value_data[td_num].text.strip())
                    key_value.append(value_data)
            else:
                key_value = self.clean_text(tr_data.select('td')[1].text.strip())
            data_data[key_name] = key_value
        return data_data

    def get_manager_senior_executive(self, title_list):
        data_data = []
        tr_data_list = title_list.select('.table-response>table>tbody>tr')
        for tr_data_num in range(len(tr_data_list)):
            if tr_data_list[tr_data_num].select('td')[0].text.strip() == "职务":
                one_people_data = {}
                td_list = tr_data_list[tr_data_num].select('td')
                for td_num in range(len(td_list)):
                    if td_list[td_num].get('class') == ['title']:
                        if td_list[td_num].text.strip() == '职务':
                            one_people_data['post'] = self.clean_text(td_list[td_num + 1].text.strip())
                        if td_list[td_num].text.strip() == '姓名':
                            one_people_data['name'] = self.clean_text(td_list[td_num + 1].text.strip())
                td_list_1 = tr_data_list[tr_data_num + 1].select('td')
                for td_num in range(len(td_list_1)):
                    if td_list[td_num].get('class') == ['title']:
                        if td_list_1[td_num].text.strip() == '是否有基金从业资格':
                            one_people_data['is_qualifications'] = self.clean_text(td_list_1[td_num + 1].text.strip())
                        if td_list_1[td_num].text.strip() == '资格获取方式':
                            one_people_data['acquisition_method'] = self.clean_text(td_list_1[td_num + 1].text.strip())
                # 工作履历
                td_list_2 = tr_data_list[tr_data_num + 2].select('.list-table')[0]
                # 获取表头
                table_head = []
                for head in td_list_2.select('thead>tr>th'):
                    table_head.append(self.table_key_en[self.clean_text(head.text.strip())])
                # 获取表数据
                work_experience = []
                for value in td_list_2.select('tbody>tr'):
                    value_data = {}
                    td_value_data = value.select('td')
                    for td_num in range(len(td_value_data)):
                        value_data[table_head[td_num]] = self.clean_text(td_value_data[td_num].text.strip())
                    work_experience.append(value_data)
                one_people_data['work_experience'] = work_experience
                data_data.append(one_people_data)
        return data_data

    def get_manager_directors_supervisors(self, title_list):
        # 获取表头
        table_table = title_list.select('.table-response>table')[0]
        table_head = []
        for head in table_table.select('thead>tr>th'):
            table_head.append(self.table_key_en[self.clean_text(head.text.strip())])
        # 获取表数据
        data_data = []
        for value in table_table.select('tbody>tr'):
            value_data = {}
            td_value_data = value.select('td')
            for td_num in range(len(td_value_data)):
                value_data[table_head[td_num]] = self.clean_text(td_value_data[td_num].text.strip())
            data_data.append(value_data)

        return data_data

    def get_manager_legal_opinion_information(self, title_list):
        data = {}
        td_list = title_list.select('.table-response>table>tbody>tr>td')
        for td_num in range(len(td_list)):
            if td_list[td_num].get('class') == ['title']:
                key_name = self.clean_text(td_list[td_num].text.strip())
                key_value = self.clean_text(td_list[td_num + 1].text.strip())
                data[key_name] = key_value
        return data

    def clean_text(self, text):
        return ' '.join(text.split()) if text else ''


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')