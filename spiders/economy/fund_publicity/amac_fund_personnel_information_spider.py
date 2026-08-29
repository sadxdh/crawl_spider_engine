import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.mysql_tools import update_set
from utils.tools import *
from utils.time_kit import *

class AmacFundPersonnelInformationSpider(BaseSpider):
    name = 'amac_fund_personnel_information'
    data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 5, 'DOWNLOAD_DELAY': 1,
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
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Origin': 'https://gs.amac.org.cn',
        'Referer': 'https://gs.amac.org.cn/amac-infodisc/res/pof/person/personOrgList.html',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    def start_requests(self):
        url = "https://gs.amac.org.cn/amac-infodisc/res/pof/person/personOrgList.html"
        yield scrapy.Request(
            url=url,
            method="GET",
            headers=self.headers,
            callback=self.get_type,
        )

    def get_type(self, response):
        soup = BeautifulSoup(response.text, 'lxml')
        for type_option in soup.select('.mod-select>option'):
            value = type_option['value']
            url = f"https://gs.amac.org.cn/amac-infodisc/api/pof/personOrg?rand=&page=0&size=20"
            yield scrapy.Request(
                url=url,
                method="POST",
                headers=self.headers,
                body=json.dumps({"page": 1, "orgType": value}).encode("utf-8"),
                callback=self.get_total_pages,
                cb_kwargs={'type_value': value},
                dont_filter=True
            )


    def get_total_pages(self, response, type_value):
        self.log_info(f"正在采集，type_value：{type_value}")
        if self.end_page < 1:
            totalpages = response.json().get('totalPages')
        else:
            totalpages = self.end_page
        if totalpages:
            for page in range(self.start_page - 1, totalpages):
                url = f"https://gs.amac.org.cn/amac-infodisc/api/pof/personOrg?rand=&page={page}&size=20"
                yield scrapy.Request(
                    url=url,
                    method="POST",
                    headers=self.headers,
                    body=json.dumps({"page":1,"orgType":type_value}).encode("utf-8"),
                    callback=self.parse_list,
                    dont_filter=True
                )

    def parse_list(self, response):
        for data_list in response.json().get('content', []):
            if data_list.get('userId'):
                userId = data_list.get('userId')
                orgType = data_list.get('orgType')
                if data_list.get('orgName'):
                    update_set(table='fund_practitioners_info', data={"status": 0}, condition=f"org_name = '{data_list.get('orgName')}'")
                yield from self.get_person_list(0, userId, orgType)

    def get_person_list(self, page, userId, orgType):
        self.log_info(f"正在采集，orgType：{orgType}， userId： {userId}，page：{page}")
        url = f"https://gs.amac.org.cn/amac-infodisc/api/pof/person?rand=&page={page}&size=20"
        payload = {
            "userId": str(userId),
            "page": 1
        }
        yield scrapy.Request(
            url=url,
            method="POST",
            headers=self.headers,
            body=json.dumps(payload).encode("utf-8"),
            callback=self.parse_person_list,
            cb_kwargs={'page': page, 'userId': userId, 'orgType': orgType},
            dont_filter=True
        )

    def parse_person_list(self, response, page, userId, orgType):
        json_data = response.json()
        for data_list in json_data.get('content', []):
            detail_api_url = f"https://gs.amac.org.cn/amac-infodisc/api/pof/person/{data_list.get('accountId')}"
            yield scrapy.Request(
                url=detail_api_url,
                method="GET",
                headers=self.headers,
                callback=self.parse_detail_person,
                cb_kwargs={'orgType': orgType},
                dont_filter=True
            )

        if page < json_data.get('totalPages', 0):
            page += 1
            yield from self.get_person_list(page, userId, orgType)

    def parse_detail_person(self, response, orgType):
        json_data = response.json()
        org_type = orgType # 机构类型
        user_name = json_data.get('userName') # 姓名
        sex = json_data.get('sex') # 性别
        org_name = json_data.get('orgName') # 从业机构
        cert_code = json_data.get('certCode') # 证书编号
        cert_name = json_data.get('certName') # 从业资格类别
        status_name = json_data.get('statusName') # 证书状态
        cert_obtain_date = self.time_localtime(json_data.get('certObtainDate')) # 证书取得日期
        person_cert_history_list = []   # 证书状态变更记录
        for history_list in json_data.get('personCertHistoryList', []):
            history_cert_code = history_list.get('certCode')    # 证书编号
            history_creation_date = self.time_localtime(history_list.get('creationDate') )   # 变更日期
            history_org_name = history_list.get('orgName')  # 从业机构
            history_cert_name = history_list.get('certName')    # 从业资格类别
            history_status_name = history_list.get('statusName')    # 证书状态
            person_cert_history_list.append({
                'history_cert_code': history_cert_code,
                'history_creation_date': history_creation_date,
                'history_org_name': history_org_name,
                'history_cert_name': history_cert_name,
                'history_status_name': history_status_name
            })
        photo_url = json_data.get('personPhotoBase64')  # 图片链接

        detail_url = f"https://gs.amac.org.cn/amac-infodisc/res/pof/person/personDetail.html?accountId={json_data['accountId']}&userId={json_data['userId']}"
        md5_value = hash_md5(user_name + sex + cert_code)


        main_item = {}
        main_item['user_name'] = user_name
        main_item['sex'] = sex
        main_item['org_name'] = org_name
        main_item['cert_code'] = cert_code
        main_item['cert_name'] = cert_name
        main_item['status_name'] = status_name
        main_item['cert_obtain_date'] = cert_obtain_date
        main_item['person_cert_history_list'] = json.dumps(person_cert_history_list, ensure_ascii=False) if person_cert_history_list else None
        main_item['photo_url'] = photo_url
        main_item['source'] = detail_url
        main_item['org_type'] = org_type
        main_item['status'] = 1
        main_item['md5_value'] = md5_value
        main_item['_table'] = 'fund_practitioners_info'
        yield main_item



    def time_localtime(self, time_data):
        if time_data:
            return time.strftime("%Y-%m-%d", time.localtime(time_data / 1000))
        else:
            return ''


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')