import hashlib, scrapy
import urllib
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.law.law_case.rmfy.manage_cookie import ManageLawCaseCookies
from utils.tools import *
from utils.time_kit import *

class RmfyCaseParseSpider(BaseSpider):
    name = 'rmfy_case_parse'
    # data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        },
        'COOKIES_ENABLED': True  #使用cookie字段必须得要
    }
    proxy_type = 'long_proxy'

    manage_cookie = ManageLawCaseCookies()
    cookies = None

    def start_requests(self):
        self.manage_cookie.generate_cookie_pool()
        for page in range(self.start_page, self.end_page + 1):
            cookie_value = self.manage_cookie.get_cookie()
            if cookie_value:
                self.cookies = cookie_value.get('cookie')
                url = "https://rmfyalk.court.gov.cn/cpws_al_api/api/cpwsAl/search"
                headers = {
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                    "Connection": "keep-alive",
                    "Content-Type": "application/json;charset=UTF-8",
                    "Origin": "https://rmfyalk.court.gov.cn",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
                    "X-Requested-With": "XMLHttpRequest",
                }
                data = {
                    "page": page,
                    "size": 50,
                    "lib": "qb",
                    "searchParams": {
                        "userSearchType": 1,
                        "isAdvSearch": "0",
                        "selectValue": "qw",
                        "lib": "cpwsAl_qb",
                        "sort_field": ""
                    }
                }
                yield scrapy.Request(
                    url=url,
                    method="POST",
                    headers=headers,
                    cookies=self.cookies,
                    body=json.dumps(data, ensure_ascii=False).encode("utf-8"),
                    callback=self.parse_detail,
                    dont_filter=True,
                )

    def parse_detail(self, response):
        results = response.json()
        for data in results["data"]["datas"]:
            url_id = data.get("id", "")
            title = data.get("cpws_al_title", "")
            cpws_al_case_sort_name = data.get('cpws_al_case_sort_name', '')
            cpws_al_sort_name = data.get('cpws_al_sort_name', '')
            case_type = f"{cpws_al_case_sort_name}-{cpws_al_sort_name}"
            court_name = data.get('cpws_al_slfy_name', '')
            trial_year = data.get('cpws_al_zs_date', '')
            main_info = data.get('cpws_al_infos', '')
            judgment_essence = data.get('cpws_al_cpyz', '')
            case_level = data.get('cpws_al_type', '')
            trial_procedure = data.get('cpws_al_slcx_name', '')
            encoded_url_id = urllib.parse.quote(url_id)

            web_url = f'https://rmfyalk.court.gov.cn/view/content.html?id={url_id}&lib=ck'

            md5_value = hash_md5(title + "人民法院案例库")

            # # item = LawCaseItem()
            # items = {}
            # # item.spider_name = self.spider_name
            # items['web_name'] = "人民法院案例库"
            # items['web_url'] = web_url
            # items['main_type'] = 1
            # items['case_type'] = case_type
            # items['title'] = title
            # items['main_info'] = main_info
            # items['judgment_essence'] = judgment_essence
            # items['md5_value'] = md5_value
            # # insert_data(table='spider_case_raw', data=item)
            # items['_table'] = 'spider_case_raw'
            # yield items

            data_value = {'url_id': url_id, 'encoded_url_id': encoded_url_id, 'court_name': court_name,
                     'trial_year': trial_year, 'case_type': case_type, 'case_level': case_level,
                     'trial_procedure': trial_procedure, 'md5_value': md5_value, 'web_url': web_url}
            # self.list_data.append(data_value)
            yield from self.get_content(data_value)

    def get_content(self, list_data):
        cookie_value = self.manage_cookie.get_cookie()
        if cookie_value:
            self.cookies = cookie_value.get('cookie')
            url_id = list_data["url_id"]
            encoded_url_id = list_data.get("encoded_url_id")

            headers = {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                "Connection": "keep-alive",
                "Content-Type": "application/json;charset=UTF-8",
                "Origin": "https://rmfyalk.court.gov.cn",
                "Referer": f"https://rmfyalk.court.gov.cn/view/content.html?id={encoded_url_id}&lib=ck",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
                "X-Requested-With": "XMLHttpRequest",
            }
            data = {
                "gid": url_id
            }
            url = "https://rmfyalk.court.gov.cn/cpws_al_api/api/cpwsAl/content"
            yield scrapy.Request(
                url=url,
                method="POST",
                headers=headers,
                cookies=self.cookies,
                body=json.dumps(data, ensure_ascii=False).encode("utf-8"),
                callback=self.parse_content,
                meta={
                    "list_data": list_data,
                },
                dont_filter=True,
            )

    def parse_content(self, response, list_data):
        result = response.json()
        data = result.get("data")
        if data:
            content = data.get("data", {})
            storage_no = content.get("cpws_al_no")
            cpws_al_keyword = content.get("cpws_al_keyword", [])
            key_words = ",".join(cpws_al_keyword)
            basic_facts = content.get("cpws_al_jbaq")
            judgment_reason = content.get("cpws_al_cply")
            judgment_essence = content.get("cpws_al_cpyz")
            judgment_result = content.get("cpws_al_cpjg")
            related_info = content.get("cpws_al_glsy")

            # item_main = CaseParseMainItem()
            item_mains = {}
            # item_main.spider_name = self.spider_name
            item_mains['web_name'] = "人民法院案例库"
            item_mains['web_url'] = list_data['web_url']
            item_mains['case_type'] = list_data['case_type']
            item_mains['storage_no'] = storage_no
            item_mains['court_name'] = list_data['court_name']
            item_mains['key_words'] = key_words
            item_mains['trial_procedure'] = list_data['trial_procedure']
            item_mains['trial_year'] = list_data['trial_year']
            item_mains['case_level'] = list_data['case_level']
            item_mains['basic_facts'] = basic_facts
            item_mains['judgment_reason'] = judgment_reason
            item_mains['judgment_essence'] = judgment_essence
            item_mains['judgment_result'] = judgment_result
            item_mains['related_info'] = related_info
            item_mains['md5_value'] = list_data['md5_value']
            # insert_data(table='case_parse_main', data=item_main)
            item_mains['_table'] = 'case_parse_main'
            yield item_mains

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')