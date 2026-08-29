"""AMAC → private_fund_register_process
旧项目参照: data_crawl_server private_fund_register.py
"""
import hashlib, random, time, scrapy
from utils.amac_fetch import amac_post
from spiders.base_spider import BaseSpider
from utils.tools import *

_LIST_URL = 'https://gs.amac.org.cn/amac-infodisc/api/pof/manager/register-flow?rand={r}&page={p}&size=20'


class AmacRegisterFlowSpider(BaseSpider):
    name = 'amac_register_flow'
    data_table = 'private_fund_register_process'
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

    def time_localtime(self, time_data):
        if time_data:
            return time.strftime("%Y-%m-%d", time.localtime(time_data / 1000))
        else:
            return ''

    def start_requests(self):
        url = f'https://gs.amac.org.cn/amac-infodisc/api/pof/manager/register-flow?rand={random.random()}&page=0&size=20'
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
            details_url = f'https://gs.amac.org.cn/amac-infodisc/api/pof/manager/register-flow?rand={random.random()}&page={page}&size=20'
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
            mechanism_name = content_data['orgName']
            mechanism_type = content_data['orgTypeName']
            processing_status = content_data['orgStatusName']
            first_submission_date = self.time_localtime(content_data['firstSubmitDate'])
            feedback_date = self.time_localtime(content_data['firstReturnNoListDate'])
            feedback_number = content_data['noListReturnCount']
            start_processing_date = self.time_localtime(content_data['auditStartDate'])
            last_feedback_date = self.time_localtime(content_data['lastUpdateDate'])
            latest_submission_date = self.time_localtime(content_data['lastSubmitDate'])
            handling_feedback_number = content_data['lastFixedCount']
            accumulated_processing_time = content_data['totalAuditDay']
            accumulated_material_time = content_data['newTotalFixedDay']
            registered_address = content_data['registerAddress']
            office_location = content_data['officeAddress']
            law_firm = content_data['latfirmName']
            lead_lawyer = content_data['legallerName']
            terminate_date = self.time_localtime(content_data['terminateDate']) # 终止办理日期
            md5_value = hash_md5(f"{mechanism_name}{first_submission_date}")

            items = {}
            items['md5_value'] = md5_value
            items['mechanism_name'] = mechanism_name
            items['mechanism_type'] = mechanism_type
            items['processing_status'] = processing_status
            items['first_submission_date'] = first_submission_date
            items['feedback_date'] = feedback_date
            items['feedback_number'] = feedback_number
            items['start_processing_date'] = start_processing_date
            items['last_feedback_date'] = last_feedback_date
            items['latest_submission_date'] = latest_submission_date
            items['handling_feedback_number'] = handling_feedback_number
            items['terminate_date'] = terminate_date
            items['accumulated_processing_time'] = accumulated_processing_time
            items['accumulated_material_time'] = accumulated_material_time
            items['registered_address'] = registered_address
            items['office_location'] = office_location
            items['law_firm'] = law_firm
            items['lead_lawyer'] = lead_lawyer
            yield items

    def errback(self, f):
        self.log_error(f'请求失败: {f.request.url}')
