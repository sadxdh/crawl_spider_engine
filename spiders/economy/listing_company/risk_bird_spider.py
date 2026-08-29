import hashlib, scrapy
from copy import deepcopy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.economy.listing_company.manage_cookie import ManageRiskBirdCookies
from utils.mysql_tools import select_data
from utils.tools import *
from utils.time_kit import *

class RiskBirdSpider(BaseSpider):
    name = 'risk_bird'
    data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        },
        #'COOKIES_ENABLED': True  # 使用cookie字段必须得要
    }
    proxy_type = 'long_proxy'

    headers = {
        "accept": "application/json",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "app-device": "WEB",
        "content-type": "application/json",
        "origin": "https://www.riskbird.com",
        "referer": "https://www.riskbird.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0",
        "xs-content-type": "application/json"
    }

    manage_cookie = ManageRiskBirdCookies()
    cookies = None

    @staticmethod
    def query_listing_company():
        datas = select_data(
            table='listing_info',
            data=['share_code', 'entity_name'],
            condition='id>0 GROUP BY share_code,entity_name',
        )
        return datas

    def get_search_hint(self, entity_name):
        url = "https://www.riskbird.com/riskbird-api/searchHint"
        params = {"queryType": "1", "key": entity_name}
        response = common_request(
            url,
            headers=self.headers,
            params=params,
            cookies=self.cookies,
            proxies_type=True
        )
        if response:
            try:
                result = response.json()
                data = result['data'][0]
                ent_id = data['entid']
                ent_name = data['entName']
                return ent_id, ent_name
            except Exception as e:
                logger.exception(f"[error] {self.name} search_hint 解析错误: {e}")
        return None, None

    def get_company_orderNo(self, entity_id, entity_name):
        url = f"https://www.riskbird.com/ent/{entity_name}.html"
        params = {"entid": entity_id}
        response = common_request(
            url,
            headers=self.headers,
            params=params,
            cookies=self.cookies,
            proxies_type=True
        )
        if response:
            try:
                order_num = self.parse_orderNo(response)
                return order_num
            except Exception as e:
                self.log_info(f"[error] {self.name} company_orderNo 解析错误: {e}")

    @staticmethod
    def parse_orderNo(response):
        # 解析html文件
        result = etree.HTML(response.text)
        datas = xpath_parse(result, '//script[@id="__NUXT_DATA__"]//text()')
        datas = json.loads(datas)
        for data in datas:
            if isinstance(data, str) and 'WEB' in data:
                return data


    def start_requests(self):
        self.manage_cookie.generate_cookie_pool()
        datas = self.query_listing_company()
        for data in datas[int(self.start_page):int(self.end_page)]:
            time.sleep(random.randint(2, 5))
            cookie_value = self.manage_cookie.get_cookie()
            if cookie_value:
                self.cookies = cookie_value.get('cookie')
                yield from self.start(data)

    def start(self, data):
        share_code = data['share_code']
        entity_name = data['entity_name']
        ent_id, ent_name = self.get_search_hint(entity_name)
        if ent_id:
            com_order_num = self.get_company_orderNo(ent_id, entity_name)
            if com_order_num:
                yield from self.company_executive(com_order_num, share_code, entity_name)

    def company_executive(self, com_order_number, share_code, entity_name):
        # 实际控制人id
        url = 'https://www.riskbird.com/riskbird-api/companyInfo/list/companyExecutive'
        json_data = {
            'filterCnd': 1,
            'page': 1,
            'size': 100,
            'orderNo': com_order_number,
            'sortField': '',
            'filterMap': {},
        }
        response = common_request(
            url,
            headers=self.headers,
            json_data=json_data,
            cookies=self.cookies,
            method='post',
            proxies_type=True
        )

        if response:
            try:
                yield from self.parse_company_executive(response, share_code, entity_name)
            except Exception as e:
                self.log_info(f"[error] {self.name} company_executive 解析错误: {e}")

    def parse_company_executive(self, response, share_code, entity_name):
        person_list = []
        result = response.json()
        api_data = result['data']['apiData']
        for data in api_data:
            person_id = data['personId']
            person_name = data['personName']
            position = data['position']

            # 存储上市公司职员信息
            # item = RiskBirdItem()
            # item.spider_name = self.spider_name
            items = {}
            items['md5_value'] = hash_md5(entity_name + person_name + position)
            items['entity_id'] = share_code
            items['entity_name'] = entity_name
            items['person_id'] = person_id
            items['person_name'] = person_name
            items['position'] = position
            # insert_data(table='listing_staff', data=item)
            items['_table'] = 'listing_staff'
            yield items

            person_list.append({'person_id': person_id, 'person_name': person_name, 'position': position, 'entity_name': entity_name})

        yield from self.get_person_list(person_list)

    def get_person_list(self, person_list):
        if person_list:
            for person in person_list:
                person_id = person['person_id']
                person_name = person['person_name']
                self.log_info(f"开始爬取关联企业 entity_name: {person['entity_name']} person_name: {person_name}")
                person_order_no = self.get_person_orderNo(person_id, person_name)
                if person_order_no:
                    yield from self.get_relate_company(person_order_no, person_id)

    def get_person_orderNo(self, person_id, person_name):
        url = f"https://www.riskbird.com/person/{person_id}.html?personName={person_name}"
        response = common_request(
            url,
            headers=self.headers,
            cookies=self.cookies,
            proxies_type=True
        )
        if response:
            try:
                order_num = self.parse_orderNo(response)
                return order_num
            except Exception as e:
                self.log_info(f"[error] {self.name} person_orderNo 解析错误: {e}")


    def get_relate_company(self, person_order_number, person_id):
        # 获取实控人关联企业
        url = 'https://www.riskbird.com/riskbird-api/query/person/personEachData'
        header = deepcopy(self.headers)
        header.pop("xs-content-type")
        json_data = {
            "pageNo": 1,
            "range": 10,
            "orderNo": person_order_number,
            "dataType": "all",
            "conpropType": "",
            "entstatus": "",
            "regionId": "",
            "nicId": ""
        }
        response = common_request(
            url,
            headers=header,
            json_data=json_data,
            cookies=self.cookies,
            method='post',
            proxies_type=True
        )
        if response:
            try:
                result = response.json()
                datas = result['data']['list']
                for data in datas:
                    entity_name = data['entname']
                    person_name = data['perName']
                    position = data.get('positionCn', '')

                    # item = RiskBirdItem()
                    # item.spider_name = self.spider_name
                    items = {}
                    items['md5_value'] = hash_md5(entity_name + person_name + position)
                    items['entity_name'] = entity_name
                    items['person_id'] = person_id
                    items['person_name'] = person_name
                    items['position'] = position
                    # insert_data(table='listing_staff', data=item)
                    items['_table'] = 'listing_staff'
                    yield items

            except Exception as e:
                self.log_info(f'[error] {self.name} relate_company 解析错误: {e}')



    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')