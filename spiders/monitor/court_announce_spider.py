"""法院公告 → entity_court_announce"""
from urllib.parse import urlencode
import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *

class CourtAnnounceSpider(BaseSpider):
    name = 'economy_court_announce'
    data_table = 'enterprise_dynamics'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "zh-CN,zh;q=0.9",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "origin": "https://rmfygg.court.gov.cn",
        "priority": "u=1, i",
        "referer": "https://rmfygg.court.gov.cn/web/rmfyportal/noticeinfo",
        "sec-ch-ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest"
    }

    @staticmethod
    def generate_data(page):
        data = {
            '_noticelist_WAR_rmfynoticeListportlet_content': '',
            '_noticelist_WAR_rmfynoticeListportlet_searchContent': '',
            '_noticelist_WAR_rmfynoticeListportlet_courtParam': '',
            '_noticelist_WAR_rmfynoticeListportlet_IEVersion': 'ie',
            '_noticelist_WAR_rmfynoticeListportlet_flag': 'init',
            '_noticelist_WAR_rmfynoticeListportlet_noticeType': '',
            '_noticelist_WAR_rmfynoticeListportlet_noticeTypeVal': '全部',
            '_noticelist_WAR_rmfynoticeListportlet_noticeSource': '',
            '_noticelist_WAR_rmfynoticeListportlet_sourceTypeVal': '全部',
            '_noticelist_WAR_rmfynoticeListportlet_isWebCountNotice': '',
            '_noticelist_WAR_rmfynoticeListportlet_aoData': '[{"name":"sEcho","value":2},'
                                                            '{"name":"iColumns","value":6},'
                                                            '{"name":"sColumns","value":",,,,,"},'
                                                            '{"name":"iDisplayStart","value":%s},'
                                                            '{"name":"iDisplayLength","value":15},'
                                                            '{"name":"mDataProp_0","value":null},'
                                                            '{"name":"mDataProp_1","value":null},'
                                                            '{"name":"mDataProp_2","value":null},'
                                                            '{"name":"mDataProp_3","value":null},'
                                                            '{"name":"mDataProp_4","value":null},'
                                                            '{"name":"mDataProp_5","value":null}]' % page
        }
        return data

    def check_down_url(self, notice_code):
        url_list = [
            f'https://rmfygg.court.gov.cn/court-service-file/{notice_code}.pdf',
            f'https://rmfygg.court.gov.cn/court-service-courtpdf/{notice_code}.pdf',
        ]

        for url in url_list:
            response = common_request(url=url, headers=self.headers, proxies_type=True)
            if response and response.status_code == 200:
                return url

        return None


    def start_requests(self):
        for page in range(self.start_page - 1, self.end_page):
            url = 'https://rmfygg.court.gov.cn/web/rmfyportal/noticeinfo'
            params = {
                'p_p_id': 'noticelist_WAR_rmfynoticeListportlet',
                'p_p_lifecycle': '2',
                'p_p_state': 'normal',
                'p_p_mode': 'view',
                'p_p_resource_id': 'initNoticeList',
                'p_p_cacheability': 'cacheLevelPage',
                'p_p_col_id': 'column-1',
                'p_p_col_count': '1',
            }
            full_url = f"{url}?{urlencode(params)}"
            data = self.generate_data(page)
            yield scrapy.FormRequest(
                url=full_url,
                method='POST',
                headers=self.headers,
                formdata=data,
                dont_filter=True,
                callback=self.parse,
            )

    def parse(self, response):
        result = response.json()
        datas = result.get('data')
        for data in datas:
            court = data.get('court')
            people = data.get('tosendPeople')
            notice_type = data.get('noticeType')
            notice_code = data.get('noticeCode')
            notice_code_enc = data.get('noticeCodeEnc')

            title = f'{court} 当事人：{people} 公告类型：{notice_type}'
            release_time = data.get('publishDate')
            content = data.get('noticeContent')
            yield from self.parse_file({'title': title, 'release_time': release_time, 'content': content, 'notice_code': notice_code})

    def parse_file(self, meta_data):
        notice_code = meta_data['notice_code']

        url = self.check_down_url(notice_code)
        title = meta_data.get('title')
        release_time = meta_data.get('release_time')
        content = meta_data.get('content')
        webanme = '人民法院公告网'

        items = {}
        items['release_time'] = release_time
        items['title'] = title
        items['url'] = url
        items['webname'] = webanme
        items['content'] = content
        items['md5_value'] = hash_md5(title + release_time + webanme)
        yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
