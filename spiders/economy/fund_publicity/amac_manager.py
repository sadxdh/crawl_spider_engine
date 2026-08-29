"""AMAC 私募基金管理人 → private_fund_manager
参照旧项目: data_crawl_server private_fund_manager.py
使用 requests 直接请求 (绕过 Scrapy Twisted TLS 指纹问题)
"""
import time
import scrapy

from spiders.base_spider import BaseSpider
from utils.tools import *


class AmacManagerSpider(BaseSpider):
    name = 'amac_manager'
    data_table = 'private_fund_manager'
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

    @staticmethod
    def replace_data(data):
        if data:
            return (data[0].strip().replace('\n', '').replace(u'\xa0', '').replace(' ', '').strip().
                    replace("'", '`').replace('"', '”'))
        else:
            return ''

    @staticmethod
    def replace_data_space(data):
        if data:
            return (data[0].strip().replace('\n', '').replace(u'\xa0', '').
                    replace("'", '`').replace('"', '”'))
        else:
            return ''

    def parse_xpath(self, path_data):
        """通用xpath解析"""
        return_xpath_data = []
        for Product_data in path_data.xpath('./td[2]/table/tbody/tr'):
            return_xpath_data.append(
                {
                    'name': self.replace_data(Product_data.xpath('./td[1]/a/text()')),
                    'Monthly_report': {
                        'Should_be_disclosed': self.replace_data(Product_data.xpath('./td[2]/text()')),
                        'undisclosed': self.replace_data(Product_data.xpath('./td[2]/span/text()'))},
                    'Quarterly_report': {
                        'Should_be_disclosed': self.replace_data(Product_data.xpath('./td[3]/text()')),
                        'undisclosed': self.replace_data(Product_data.xpath('./td[3]/span/text()'))},
                    'Half_year_report': {
                        'Should_be_disclosed': self.replace_data(Product_data.xpath('./td[4]/text()')),
                        'undisclosed': self.replace_data(Product_data.xpath('./td[4]/span/text()'))},
                    'annual_report': {
                        'Should_be_disclosed': self.replace_data(Product_data.xpath('./td[5]/text()')),
                        'undisclosed': self.replace_data(Product_data.xpath('./td[5]/span/text()'))},
                    'Account_opening_rate': self.replace_data(Product_data.xpath('./td[6]/text()'))
                }
            )
        return return_xpath_data

    def parse_executive_information(self, data):
        executive_information = []
        for i in range(0, len(data), 3):
            work_experience_list = [self.parse_work_experience(experience) for experience in
                                    data[i + 2].xpath('./td[2]/table/tbody/tr')]
            single_executive = {
                'post': self.replace_data_space(data[i].xpath('./td[2]/text()')),
                'name': self.replace_data(data[i].xpath('./td[4]/text()')),
                'is_qualifications': self.replace_data(data[i + 1].xpath('./td[2]/text()')),
                'acquisition_method': self.replace_data(data[i + 1].xpath('./td[4]/text()')),
                'work_experience': work_experience_list
            }
            executive_information.append(single_executive)
        return executive_information

    def parse_work_experience(self, data):
        return {
            'time': self.replace_data(data.xpath('./td[1]/text()')),
            'company': self.replace_data(data.xpath('./td[2]/text()')),
            'department': self.replace_data(data.xpath('./td[3]/text()')),
            'post': self.replace_data(data.xpath('./td[4]/text()'))
        }

    def parse_related_party(self, data):
        return {
            'serial_number': self.replace_data(data.xpath('./td[1]/text()')),
            'type': self.replace_data(data.xpath('./td[2]/text()')),
            'name': self.replace_data(data.xpath('./td[3]/a/text()')),
            'registration_number': self.replace_data(data.xpath('./td[4]/text()')),
            'institution_code': self.replace_data(data.xpath('./td[5]/text()'))
        }

    def parse_investor(self, data):
        return {
            'serial_number': self.replace_data(data.xpath('./td[1]/text()')),
            'name': self.replace_data(data.xpath('./td[2]/text()')),
            'subscription_ratio': self.replace_data(data.xpath('./td[3]/text()'))
        }

    def parse_product_information(self, data):
        return {
            'interest_rate': self.replace_data(data[0].xpath('./td[2]/text()')),
            'former_fund': self.parse_xpath(data[1]),
            'post_fund': self.parse_xpath(data[2]),
            'consulting_products': self.parse_xpath(data[3]),
        }

    def parse_reminder_information(self, data):
        integrity_information = [self.parse_integrity_info(row) for row in data[0].xpath('./td[2]/table/tbody/tr')]
        reminder_information = [self.parse_reminder(row) for row in data[2].xpath('./td[2]/table/tbody/tr')]
        administrator_change = self.parse_administrator_change(data[4].xpath('./td[2]/table/tbody/tr')) if data[
            4].xpath('./td[2]/table/tbody/tr') else None

        return {
            'integrity_information': integrity_information,
            'reminder_information': reminder_information,
            'administrator_change': administrator_change
        }

    def parse_integrity_info(self, data):
        return {
            'title': self.replace_data(data.xpath('./td[1]/text()')),
            'info': self.replace_data(data.xpath('./td[2]//text()'))
        }

    def parse_reminder(self, data):
        return {
            'title': self.replace_data(data.xpath('./td[1]/text()')),
            'info': self.replace_data(data.xpath('./td[2]//text()'))
        }

    def parse_administrator_change(self, data):
        return {
            'submission_time': self.replace_data(data[0].xpath('./td[2]//text()')),
            'change_info': self.replace_data(data[1].xpath('./td[2]//text()')),
            'type': self.replace_data(data[2].xpath('./td[2]//text()'))
        }

    @staticmethod
    def parse_item1(content_data):
        data = {
            'manager_name': content_data['managerName'],  # 私募基金管理人名称
            'legal_person': content_data.get('artificialPersonName'),  # 法定代表人/执行事务合伙人(委派代表)姓名
            'organization_type': content_data.get('primaryInvestType'),  # 机构类型
            'registration_number': content_data.get('registerNo'),  # 登记编号
            # 'registration_location': content_data.get('regAdrAgg'),  # 注册地
            # 'office_location': content_data.get('officeAdrAgg'),  # 办公地
            'founded_date': time.strftime("%Y-%m-%d",
                                          time.localtime(content_data['establishDate'] / 1000)),
            # founded_date	成立时间,  # 成立时间
            'registration_date': time.strftime("%Y-%m-%d", time.localtime(
                content_data['registerDate'] / 1000)),  # registration_date	登记时间
            'fund_number': content_data['fundCount'],  # 在管基金数量
            'personnel_type': content_data.get('memberType'),  # 会员类型
            'is_tip_info': '是' if content_data['hasSpecialTips'] else '否',  # 是否有特别提示
            'is_faith_info': '是' if content_data['hasCreditTips'] else '否'  # 是否有诚信信息
        }
        return data

    def parse_item2(self, response):
        tree = etree.HTML(response.body)
        # 基金规模
        fund_size = self.replace_data(
            tree.xpath('//div[@class="info-body"]/div[2]/div[2]/table/tbody/tr[last()-1]/td[2]/text()'))
        # 机构信息
        data_xpath_tr = tree.xpath('//div[@class="info-body"]/div[2]/div[@class="table-response"]/table/tbody/tr')
        manager_name_en = self.replace_data(data_xpath_tr[1].xpath('./td[2]/text()'))  # 基金管理人全称(英文)
        registration_location = self.replace_data(data_xpath_tr[6].xpath('./td[2]/text()'))  # 注册地
        office_location = self.replace_data(data_xpath_tr[7].xpath('./td[2]/text()'))  # 办公地
        organizational_code = self.replace_data(data_xpath_tr[3].xpath('./td[2]/text()'))
        registered_capital = self.replace_data(data_xpath_tr[8].xpath('./td[2]/text()'))
        paid_in = self.replace_data(data_xpath_tr[9].xpath('./td[2]/text()'))
        registration_ratio = self.replace_data(data_xpath_tr[10].xpath('./td[2]/text()'))
        enterprise_nature = self.replace_data(data_xpath_tr[11].xpath('./td[2]/text()'))
        business_type = self.replace_data(data_xpath_tr[13].xpath('./td[2]/text()'))
        full_time_staff = self.replace_data(data_xpath_tr[14].xpath('./td[2]/text()'))
        number_of_fund_members = self.replace_data(data_xpath_tr[15].xpath('./td[2]/text()'))
        # 机构信息最后更新时间
        institutional_update_time = self.replace_data(data_xpath_tr[18].xpath('./td[2]/text()')) if len(
            data_xpath_tr) > 18 else self.replace_data(data_xpath_tr[17].xpath('./td[2]/text()')) if len(
            data_xpath_tr) > 17 else None
        # 会员信息
        member_data = tree.xpath('//div[@class="info-body"]/div[3]/div[@class="table-response"]/table/tbody/tr')
        is_member = member_representative = member_type = membership_time = ''
        if member_data:
            data = member_data[0]
            if data:
                is_member = self.replace_data(data.xpath('./td[2]/text()'))
                member_representative = self.replace_data(data.xpath('./td[4]/text()'))
            data = member_data[1] if len(member_data) > 1 else None
            if data:
                member_type = self.replace_data(data.xpath('./td[2]/text()'))
                membership_time = self.replace_data(data.xpath('./td[4]/text()'))

        # 法律意见书信息
        law_data = tree.xpath('//div[@class="info-body"]/div[4]/div[@class="table-response"]/table/tbody/tr')
        legal_opinion_status = name_of_law_firm = lawyer_name = ''
        if law_data:
            data = law_data[0]
            if data:
                legal_opinion_status = self.replace_data(law_data[0].xpath('./td[2]/text()'))
            data = law_data[1] if len(law_data) > 1 else None
            if data:
                name_of_law_firm = self.replace_data(law_data[1].xpath('./td[2]/text()'))
                lawyer_name = self.replace_data(law_data[1].xpath('./td[4]/text()'))

        # 高管信息
        executive_data = tree.xpath('//div[@class="info-body"]/div[6]/div[@class="table-response"]/table/tbody/tr')
        executive_information = self.parse_executive_information(executive_data)
        # 关联方信息
        related_data_tr = tree.xpath(
            '//div[@class="info-body"]/div[7]/div[@class="table-response"]/table/tbody/tr/td[2]/table/tbody/tr')
        related_party_information = [self.parse_related_party(row) for row in related_data_tr]
        # 出资人信息
        investor_data_tr = tree.xpath(
            '//div[@class="info-body"]/div[8]/div[@class="table-response"]/table/tbody/tr/td[2]/table/tbody/tr')
        investor_information = [self.parse_investor(row) for row in investor_data_tr]
        # 产品信息
        product_data_tr = tree.xpath('//div[@class="info-body"]/div[10]/div[@class="table-response"]/table/tbody/tr')
        product_information = self.parse_product_information(product_data_tr)
        # 机构提示，诚信信息，最近重大变更
        reminder_data_tr = tree.xpath('//div[@class="info-body"]/div[1]/div[@class="table-response"]/table/tbody/tr')
        reminder_information = self.parse_reminder_information(reminder_data_tr)
        result = {
            'fund_size': fund_size,
            'manager_name_en': manager_name_en,
            'registration_location': registration_location,
            'office_location': office_location,
            'organizational_code': organizational_code,
            'registered_capital': registered_capital,
            'paid_in': paid_in,
            'registration_ratio': registration_ratio,
            'enterprise_nature': enterprise_nature,
            'business_type': business_type,
            'full_time_staff': full_time_staff,
            'number_of_fund_members': number_of_fund_members,
            'institutional_update_time': institutional_update_time,
            'is_member': is_member,
            'member_representative': member_representative,
            'member_type': member_type,
            'membership_time': membership_time,
            'legal_opinion_status': legal_opinion_status,
            'name_of_law_firm': name_of_law_firm,
            'lawyer_name': lawyer_name,
            'executive_information': executive_information,
            'related_party_information': related_party_information,
            'investor_information': investor_information,
            'product_information': product_information,
            'reminder_information': reminder_information,
        }
        return result

    def start_requests(self):
        url = f'https://gs.amac.org.cn/amac-infodisc/api/pof/manager/query?&page=0&size=20'
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
            details_url = f'https://gs.amac.org.cn/amac-infodisc/api/pof/manager/query?&page={page}&size=20'
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
        response = response.json()
        for content_data in response['content']:
            url = 'https://gs.amac.org.cn/amac-infodisc/res/pof/manager/' + content_data[
                'url']  # details_url	基金公示信息url（跳转到第三方页面）

            data1 = self.parse_item1(content_data)
            yield scrapy.Request(
                url=url,
                headers=self.headers,
                method='GET',
                errback=self.errback,
                callback=self.parse_items,
                dont_filter=True,
                cb_kwargs={'data1': data1, 'url': url}
            )

    def parse_items(self, response, data1, url):
        try:
            data2 = self.parse_item2(response)
            md5_value = hash_md5(data1['manager_name'] + data1['registration_number'])
            items = {}
            items['md5_value'] = md5_value
            items['manager_name'] = data1['manager_name']
            items['legal_person'] = data1['legal_person']
            items['organization_type'] = data1['organization_type']
            items['registration_number'] = data1['registration_number']
            # items['registration_location'] = data1['registration_location']
            # items['office_location'] = data1['office_location']
            items['founded_date'] = data1['founded_date']
            items['registration_date'] = data1['registration_date']
            items['fund_number'] = data1['fund_number']
            items['personnel_type'] = data1['personnel_type']
            items['is_faith_info'] = data1['is_faith_info']
            items['is_tip_info'] = data1['is_tip_info']

            items['fund_url'] = url
            items['fund_size'] = data2['fund_size']
            items['manager_name_en'] = data2['manager_name_en']
            items['registration_location'] = data2['registration_location']
            items['office_location'] = data2['office_location']
            items['Organizational_code'] = data2['organizational_code']
            items['registered_capital'] = data2['registered_capital']
            items['Paid_in'] = data2['paid_in']
            items['Registration_ratio'] = data2['registration_ratio']
            items['Enterprise_nature'] = data2['enterprise_nature']
            items['Business_type'] = data2['business_type']
            items['Full_time_staff'] = data2['full_time_staff']
            items['Number_of_Fund_Members'] = data2['number_of_fund_members']
            items['Institutional_update_time'] = data2['institutional_update_time']
            items['is_member'] = data2['is_member']
            items['Member_representative'] = data2['member_representative']
            items['Member_type'] = data2['member_type']
            items['Membership_time'] = data2['membership_time']
            items['Legal_Opinion_Status'] = data2['legal_opinion_status']
            items['Name_of_Law_Firm'] = data2['name_of_law_firm']
            items['lawyer_name'] = data2['lawyer_name']
            items['Executive_Information'] = json.dumps(data2['executive_information'], ensure_ascii=False)
            items['Related_party_information'] = json.dumps(data2['related_party_information'], ensure_ascii=False)
            items['Investor_Information'] = json.dumps(data2['investor_information'], ensure_ascii=False)
            items['Product_Information'] = json.dumps(data2['product_information'], ensure_ascii=False)
            items['Reminder_information'] = json.dumps(data2['reminder_information'], ensure_ascii=False)
            yield items
        except Exception as e:
            self.log_info(f"数据提取失败，url：{url}，e：{e}")


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
