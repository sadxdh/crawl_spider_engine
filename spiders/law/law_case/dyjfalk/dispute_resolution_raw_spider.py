import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *
from spiders.law.law_case.dyjfalk.manage_cookie import ManageLawCaseDyCookies

class DisputeResolutionRawSpider(BaseSpider):
    name = 'dispute_resolution_raw'
    # data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        # 'DOWNLOADER_MIDDLEWARES': {
        #     'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        # }
    }
    proxy_type = 'no_proxy'

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://dyjfalk.court.gov.cn',
        'Pragma': 'no-cache',
        'Referer': 'https://dyjfalk.court.gov.cn/site/search',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0',
    }
    manage_cookie = ManageLawCaseDyCookies()

    def generate_headers(self):
        cookie_value = self.manage_cookie.get_cookie()
        if cookie_value:
            cookies = cookie_value.get('cookie').get('DyjfAlkInternet-Token')
            return cookies
        return None

    def start_requests(self):
        self.manage_cookie.generate_cookie_pool()
        for page in range(self.start_page, self.end_page + 1):
            url = 'https://dyjfalk.court.gov.cn/dyjfAlkInternet-admin/s'
            json_data = {
                'pageNum': page,
                'pageSize': 50,
                'orderByColumn': 'caseWarehousingTime',
                'searchConditions': [],
            }
            cookies = self.generate_headers()
            if cookies:
                headers = self.headers.copy()
                headers['Authorization'] = f'Bearer {cookies}'
                headers['Content-Type'] = 'application/json;charset=UTF-8'

                yield scrapy.Request(
                    url=url,
                    method='POST',
                    headers=headers,
                    body=json.dumps(json_data, ensure_ascii=False),
                    callback=self.parse_list,
                )

    def parse_list(self, response):
        result = response.json()
        rows = result.get('rows', [])
        for row in rows:
            case_id = row.get('caseId')
            title = row.get('caseTitle')
            case_code_name = row.get('caseCodeName', '')
            dispute_code_name = row.get('disputeCodeName', '')
            case_type = f"{case_code_name}-{dispute_code_name}"
            court_name = row.get('courtName', '')
            trial_year = row.get('caseOfflineTime')

            web_url = f'https://dyjfalk.court.gov.cn/site/case/{case_id}'

            # 主要信息
            case_no = row.get('caseNo')
            # 调解单位, 解纷没有一审二审, 未知是指导性案例还是参考案例
            units = row.get('resolveUnitsInfos')
            mediation_unit = [unit.get('caseResolveUnitsName') for unit in units]
            mediation_unit = ' '.join(mediation_unit)
            main_info = ' /'.join([case_no, case_code_name, dispute_code_name, court_name, mediation_unit])

            judgment_essence = row.get('caseGist')
            md5_value = hash_md5(title + "多元解纷案例库")

            items = {}
            # item.spider_name = self.spider_name
            items['web_name'] = "多元解纷案例库"
            items['web_url'] = web_url
            items['main_type'] = 3
            items['case_type'] = case_type
            items['title'] = title
            items['main_info'] = main_info
            items['judgment_essence'] = judgment_essence
            items['md5_value'] = md5_value
            # insert_data(table='spider_case_raw', data=item)
            items['_table'] = 'spider_case_raw'
            yield items

            # storage_no = row.get('caseNo')
            # keywords = row.get('keywords', [])
            # key_words = ','.join(keywords)
            # basic_facts = row.get('caseBaseIfno')
            # judgment_reason = row.get('caseProcessMethod')
            # judgment_result = row.get('caseSolutionResault')
            # related_info = row.get('caseAccording')
            #
            # item_mains = {}
            # # item_main.spider_name = self.spider_name
            # item_mains['web_name'] = "多元解纷案例库"
            # item_mains['web_url'] = web_url
            # item_mains['case_type'] = case_type
            # item_mains['storage_no'] = storage_no
            # item_mains['court_name'] = court_name
            # item_mains['key_words'] = key_words
            # item_mains['trial_year'] = trial_year
            # item_mains['basic_facts'] = basic_facts
            # item_mains['judgment_reason'] = judgment_reason
            # item_mains['judgment_essence'] = judgment_essence
            # item_mains['judgment_result'] = judgment_result
            # item_mains['related_info'] = related_info
            # item_mains['md5_value'] = md5_value
            # # insert_data(table='case_parse_main', data=item_main)
            # item_mains['table'] = 'case_parse_main'
            # yield item_mains


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')