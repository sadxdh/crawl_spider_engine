import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class GroupStandardSpider(BaseSpider):
    name = 'entity_group_standard'
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
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://www.ttbz.org.cn",
        "Pragma": "no-cache",
        # "Referer": "https://www.ttbz.org.cn/standard.html",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
        "sec-ch-ua": "\"Google Chrome\";v=\"147\", \"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"147\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    def start_requests(self):
        # 社会团体栏目数据
        base_url = "https://www.ttbz.org.cn/cms-proxy/ms/district/portal/getProvince"
        yield scrapy.http.JsonRequest(
            url=base_url,
            method="POST",
            headers=self.headers,
            data={},
            callback=self.parse_area,
            dont_filter=True,
        )
        # 团体标准栏目数据
        for page in range(self.start_page, self.end_page + 1):
            base_url = "https://www.ttbz.org.cn/cms-proxy/ms/portal/standardInfo/getPortalStandardList"

            data = {
                "pageNo": str(page),
                "pageSize": "50",
                "standardStatus": "1",
            }
            yield scrapy.FormRequest(
                url=base_url,
                method="POST",
                headers=self.headers,
                formdata=data,
                callback=self.parse_list,
                dont_filter=True,
            )


    def parse_area(self, response):
        data_data = response.json()['data']
        data_data.insert(0, {'name': ''})
        for area in data_data:
            # area_group = self.get_area_group(area['name'])
            area_name = area['name']
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "application/json",
                "Origin": "https://www.ttbz.org.cn",
                "Pragma": "no-cache",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
                "sec-ch-ua": "\"Google Chrome\";v=\"147\", \"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"147\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"Windows\"",
            }
            base_url = "https://www.ttbz.org.cn/cms-proxy/ms/bus/organList/portal/queryOrgan"
            params = {
                "pageNo": "1",
                "pageSize": "100",
            }
            data = {
                "certUnitArea": area_name,
            }
            request_url = f"{base_url}?{urlencode(params)}"

            yield scrapy.http.JsonRequest(
                url=request_url,
                method="POST",
                headers=headers,
                data=data,
                callback=self.parse_organ_list,
                dont_filter=True,
            )

    def parse_organ_list(self, response):
        area_group = response.json()['data']['rows']
        for row in area_group:
            base_url = "https://www.ttbz.org.cn/cms-proxy/ms/portal/standardInfo/getPortalStandardList"
            organUniqueId = row['organUniqueId']
            data = {
                "pageNo": "1",
                "pageSize": "100",
                "standardStatus": "1",
                "organUniqueId": organUniqueId,
            }

            yield scrapy.FormRequest(
                url=base_url,
                method="POST",
                headers=self.headers,
                formdata={k: str(v) for k, v in data.items()},
                callback=self.parse_list,
                dont_filter=True,
            )

    def parse_list(self, response):
        data_json = response.json()
        for row in data_json['data']['rows']:
            standardTitleCn = row['standardTitleCn']
            standardTitleEn = row['standardTitleEn']
            standardNo = row['standardNo']
            standardStatusName = row['standardStatusName']
            publishDate = row['publishDate']
            implementDate = row['implementDate']
            abolishDate = row['abolishDate']
            organName = row['organName']
            standardUniqueId = row['standardUniqueId']
            temp = {
                'standard_name': standardTitleCn,
                'standard_en_name': standardTitleEn,
                'standard_num': standardNo,
                'standard_status': standardStatusName,
                'publish_date': publishDate,
                'implement_date': implementDate,
                'abolish_date': abolishDate,
                'group_name': organName,
                'standardUniqueId': standardUniqueId
            }
            self.log_info(temp)
            # base_url = "https://www.ttbz.org.cn/cms-proxy/ms/portal/standardInfo/getPortalStandardById"
            # data = {
            #     "id": id,
            # }
            # yield scrapy.FormRequest(
            #     url=base_url,
            #     method="POST",
            #     headers=self.headers,
            #     formdata={k: str(v) for k, v in data.items()},
            #     callback=self.parse_detail,
            #     cb_kwargs={
            #         "detail_data": temp,
            #     },
            #     dont_filter=True,
            # )
            base_url = f"https://www.ttbz.org.cn/standardDetail/{standardUniqueId}.html"
            yield scrapy.Request(
                url=base_url,
                headers=self.headers,
                callback=self.parse_detail,
                cb_kwargs={'detail_data': temp}
            )

    def parse_detail(self, response, detail_data):
        soup = BeautifulSoup(response.text, 'lxml')
        json_text = soup.select('#portal-standard-detail-json')[0].text
        data_json = json.loads(json_text)
        if data_json:
            international_standard_class_num = data_json.get('icsl1Name')
            china_standard_class_num = data_json.get('ccss1Name')
            national_economy_class = data_json.get('ccsl1Name')
            drafting_unit = data_json.get('editorUnit')
            drafter = data_json.get('drafterNames')
            standard_range = data_json.get('scope')
            technical_content = data_json.get('mainContent')
            including_patent_info = data_json.get('isPatentName')

            items = {}
            items['standard_name'] = detail_data.get('standard_name')
            items['standard_en_name'] = detail_data.get('standard_en_name')
            items['standard_num'] = detail_data.get('standard_num')
            items['standard_status'] = detail_data.get('standard_status')
            items['standard_level'] = '团体标准'
            items['publish_date'] = detail_data.get('publish_date')
            items['implement_date'] = detail_data.get('implement_date')
            items['abolish_date'] = detail_data.get('abolish_date')
            items['international_standard_class_num'] = international_standard_class_num
            items['china_standard_class_num'] = china_standard_class_num
            items['national_economy_class'] = national_economy_class
            items['group_name'] =detail_data.get('group_name')
            items['drafting_unit'] = drafting_unit
            items['drafter'] = drafter
            items['standard_range'] = standard_range
            items['technical_content'] = technical_content
            items['including_patent_info'] = including_patent_info
            items['md5_value'] = hash_md5(detail_data['standard_num'] + detail_data['standard_status'])
            # insert_data(table='entity_standard_info', data=item)
            yield items


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')