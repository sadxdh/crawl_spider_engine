import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class MinistryJusticeSpider(BaseSpider):
    name = 'ministry_justice'
    data_table = 'law_regulation'
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    }
    start_urls = [
        # 中国法律服务网\首页 > 寻鉴定 > 政策法规
        {
            'url': 'https://www.12348.gov.cn/pub/12348/xjd/flfg/index.html',
            'data': '',
            'page': 2,
            'url_type': '政策法规'
        },
        # 中华人民共和国司法部\首页 > 机构设置 > 直属单位 > 法律援助中心 > 政策信息 > 政策法规 > 规章和司法解释
        {
            'url': 'https://www.moj.gov.cn/pub/sfbgw/jgsz/jgszzsdw/zsdwflyzzx/flyzzxzcxx/zcxxzcfg/zcfggzhsfjs/index.html',
            'data': '',
            'page': 2,
            'url_type': '规章和司法解释'
        },
        # 中华人民共和国司法部\法定主动公开内容 > 履职依据>司法行政相关法律法规
        {
            'url': 'https://www.moj.gov.cn/pub/sfbgw/zwxxgk/fdzdgknr/fdzdgknrlzyj/index.html',
            'data': '',
            'page': 6,
            'url_type': '司法行政相关法律法规'
        },
        # 中华人民共和国司法部\政策 >司法部规章
        # https://www.moj.gov.cn/pub/sfbgw/zwxxgk/zfxxgkzc/index.html
        {
            'url': 'https://www.moj.gov.cn/policyManager/policy/getPolicyDocList',
            'data': {"pageNum": "1", "file_type": "1", "validity": "1", "file_status": "1", "pageSize": 10},
            'page': 6,
            'url_type': '司法部规章'
        },
    ]

    def start_requests(self):
        for base_data in self.start_urls:
            all_page = 1 if int(self.end_page) == 1 else int(base_data['page'])
            for page in range(self.start_page, all_page + 1):
                if base_data['data'] == '':
                    base_url = base_data['url']
                    if page != 1:
                        page_number = page - 1
                        base_url = re.sub(r'\.html', f'_{page_number}.html', base_url)
                    response = common_request(base_url, headers=self.headers, proxies_type=True)
                else:
                    headers = {
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
                    }
                    base_url = base_data['url']
                    base_data['data']['pageNum'] = str(page)
                    data = json.dumps(base_data['data'], separators=(',', ':'))
                    response = common_request(base_url, data=data, headers=headers, method='POST', proxies_type=True)
                if response:
                    yield from self.parse_list(response, base_data)

    def parse_list(self, response, base_data):
        if base_data['url_type'] == '政策法规':
            soup = BeautifulSoup(response.text, 'lxml')
            for li in soup.select('.proInf>ul>li'):
                content_url = urljoin(base_data['url'], li.a['href'])
                if 'www.12348.gov.cn' not in content_url:
                    continue
                title = li.a['title']
                publish_date = li.select('.proliRig')[0].text.strip().replace('[', '').replace(']', '')
                url_list = {
                    'title': title,
                    'publish_date': publish_date,
                    'content_url': content_url,
                    'url_type': base_data['url_type']
                }
                yield from self.get_content(url_list)
        elif base_data['url_type'] == '规章和司法解释':
            soup = BeautifulSoup(response.text, 'lxml')
            for li in soup.select('.news_list>ul>li'):
                content_url = urljoin(base_data['url'], li.a['href'])
                if 'www.moj.gov.cn' not in content_url:
                    continue
                publish_date = li.select('.article-time')[0].text.strip()
                url_list = {
                    'publish_date': publish_date,
                    'content_url': content_url,
                    'url_type': base_data['url_type']
                }
                yield from self.get_content(url_list)
        elif base_data['url_type'] == '司法行政相关法律法规':
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            for li in soup.select('.guideArea')[0].select('ul>li'):
                content_url = urljoin(base_data['url'], li.a['href'])
                if 'www.moj.gov.cn' not in content_url:
                    continue
                publish_date = li.select('.time')[0].text.strip()
                url_list = {
                    'publish_date': publish_date,
                    'content_url': content_url,
                    'url_type': base_data['url_type']
                }
                yield from self.get_content(url_list)
        elif base_data['url_type'] == '司法部规章':
            json_data = json.loads(response.text)
            for li in json_data['list']:
                content_url = f"https://www.moj.gov.cn/policyManager/regulationDetail.html?showMenu=false&showFileType=1&pkid={li['aritcleid']}"
                publish_date = li['release_date']
                title = li['document_title']
                url_list = {
                    'publish_date': publish_date,
                    'content_url': content_url,
                    'title': title,
                    'aritcleid': li['aritcleid'],
                    'url_type': base_data['url_type']
                }
                yield from self.get_content(url_list)


    def get_content(self, list_data):
        if list_data['url_type'] != '司法部规章':
            url = list_data['content_url']
            response = common_request(url, headers=self.headers, proxies_type=True)
        else:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
            }
            post_url = "https://www.moj.gov.cn/policyManager/policy/getPolicyDocDetail"
            data = {
                "pageNum": 1,
                "pageSize": 15,
                "searchType": 1,
                "validity": "1",
                "file_type": 1,
                "file_status": "1",
                "skipPage": "",
                "pkid": list_data['aritcleid']
            }
            data = json.dumps(data, separators=(',', ':'))
            response = common_request(post_url, data=data, headers=headers, method='POST', proxies_type=True)
        if response:
            data_data = self.content_data(response, list_data)
            yield from self.parse_content(data_data)


    def content_data(self, response, list_data):
        if '政策法规' == list_data['url_type']:
            return None
        elif '规章和司法解释' == list_data['url_type']:
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            try:
                title = soup.select('h1.phone_size1')[0].text.strip()
                md5_value = hash_md5(f"{list_data['content_url']}{title}")
                content = str(soup.select('[class="newM"]')[0].text)
            except:
                return None
            try:
                formulating_authority = soup.select('[class="sT_left"]>span')[0].text.strip().replace('来源：', '')
            except:
                formulating_authority = None
            data_data = {
                'md5_value': md5_value,
                'source': list_data['content_url'],
                'title': title,
                'formulating_authority': formulating_authority,
                'law_nature': None,
                'timeliness': None,
                'publish_date': list_data['publish_date'],
                'law_category': None,
                'entry_into_force_time': None,
                'announcement_title': None,
                'announcement_url': None,
                'oss_url': None,
                'content': content
            }
        elif '司法行政相关法律法规' == list_data['url_type']:
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            title = soup.select('.listMain>h1')[0].text.strip()
            md5_value = hash_md5(f"{list_data['content_url']}{title}")
            content = str(soup.select('.listMain>.lCont')[0].text)
            try:
                formulating_authority = soup.select('.listMain>.ly')[0].text.strip().split(' ')[0].replace('来源：', '')
            except:
                formulating_authority = None
            data_data = {
                'md5_value': md5_value,
                'source': list_data['content_url'],
                'title': title,
                'formulating_authority': formulating_authority,
                'law_nature': None,
                'timeliness': None,
                'publish_date': list_data['publish_date'],
                'law_category': None,
                'entry_into_force_time': None,
                'announcement_title': None,
                'announcement_url': None,
                'oss_url': None,
                'content': content
            }
        elif '司法部规章' == list_data['url_type']:
            json_data = response.json()
            md5_value = hash_md5(f"{list_data['content_url']}{list_data['title']}")
            formulating_authority = json_data['data']['publisher']
            content = BeautifulSoup(json_data['data']['document_content'], 'lxml').text
            announcement_title = json_data['data']['picVersionFile']['filename']
            announcement_url = f"https://www.moj.gov.cn/policyManager/attach/downloadFile?realfilename={json_data['data']['picVersionFile']['_id']}"
            data_data = {
                'md5_value': md5_value,
                'source': list_data['content_url'],
                'title': list_data['title'],
                'formulating_authority': formulating_authority,
                'law_nature': None,
                'timeliness': None,
                'publish_date': list_data['publish_date'],
                'law_category': None,
                'entry_into_force_time': None,
                'announcement_title': announcement_title,
                'announcement_url': announcement_url,
                'oss_url': None,
                'content': content
            }
        return data_data

    def parse_content(self, data_data):
        if data_data:
            # item_main = LawRegulationItem()
            item_mains = {}
            # item_main.spider_name = self.spider_name
            item_mains['md5_value'] = data_data['md5_value']
            item_mains['source'] = data_data['source']
            item_mains['title'] = data_data['title']
            item_mains['formulating_authority'] = data_data['formulating_authority']
            item_mains['law_nature'] = data_data['law_nature']
            item_mains['timeliness'] = data_data['timeliness']
            item_mains['publish_date'] = data_data['publish_date']
            item_mains['law_category'] = data_data['law_category']
            item_mains['entry_into_force_time'] = data_data['entry_into_force_time']
            item_mains['announcement_title'] = data_data['announcement_title']
            item_mains['announcement_url'] = data_data['announcement_url']
            item_mains['oss_url'] = data_data['oss_url']
            item_mains['content'] = data_data['content'].replace('\u3000', ' ').replace('\xa0', ' ')
            # insert_data(table='law_regulation', data=item_main)
            yield item_mains

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')