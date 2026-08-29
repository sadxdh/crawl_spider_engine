import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class DisabilityAssessmentSpider(BaseSpider):
    name = 'disability_assessment'
    data_table = 'law_regulation'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        },
        'COOKIES_ENABLED': True  # 使用cookie字段必须得要
    }
    proxy_type = 'long_proxy'

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    }

    base_url = "https://www.mohrss.gov.cn/xxgk2020/gzk/gzjs/" # 来源页面

    def get_cookie(self, response):
        cookie = {}
        wtkkn = re.findall(r'WTKkN:(.*?),', response.text)[0]
        boydu = re.findall(r'bOYDu:(.*?),', response.text)[0]
        wyecn = re.findall(r'wyeCN:(.*?),', response.text)[0]
        EO_Bot_Ssid = re.findall(r'case"3":t=a\[.*?\]\(t,(.*?)\);', response.text)[0]
        cookie['EO_Bot_Ssid'] = EO_Bot_Ssid
        cookie['__tst_status'] = str(int(wtkkn) + int(boydu) + int(wyecn))
        return cookie

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            url = "https://www.mohrss.gov.cn/was5/web/search"
            params = {
                "channelid": "216694",
                "searchword": "",
                "searchscope": "",
                "title": "",
                "content": "",
                "fwzh": "",
                "page": str(page),
                "releasedatehiddenstart": "",
                "releasedatehiddenend": "",
                "replacedstandardhiddenstart": "",
                "replacedstandardhiddenend": ""
            }
            full_url = f"{url}?{urlencode(params)}"
            yield scrapy.Request(
                url=full_url,
                method="GET",
                headers=self.headers,
                callback=self.parse_list,
                dont_filter=True,
            )

    def parse_list(self, response):
        soup = BeautifulSoup(response.text, 'lxml')
        for li in soup.select('.gz_list>ul>li'):
            content_url = urljoin('https://www.mohrss.gov.cn/xxgk2020/gzk/gzjs/', li.select('.title>a')[0]['href'])
            title = li.select('.title>a')[0].text.strip()
            date_text = li.select('.title>p')[0].text.strip()
            publish_date = re.findall(r"\d{4}年\d{1,2}月\d{1,2}日", date_text)[0].replace("年", "-").replace("月", "-").replace("日", "")
            announcement_url = li.select('[class="download pc_none"] a')[1]['href'].replace('http://', 'https://')
            url_list = {
                'title': title,
                'publish_date': publish_date,
                'content_url': content_url,
                'announcement_title': title,
                'announcement_url': announcement_url
            }
            yield from self.get_content(url_list)

    def get_content(self, list_data):
        url = list_data['content_url']
        proxies = get_seesion_proxies()
        response = requests.get(url, headers=self.headers, proxies=proxies)
        if 'WTKkN' in response.text:
            cookie = self.get_cookie(response)
            response = requests.get(url, headers=self.headers, proxies=proxies, cookies=cookie)
        if response:
            data_data = self.content_data(response, list_data)
            yield from self.parse_content(data_data)


    def content_data(self, response, list_data):
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'lxml')
        md5_value = hash_md5(f"{list_data['content_url']}{list_data['title']}")
        try:
            content = soup.select('.gz_content')[0].text.replace('\u3000', ' ').replace('\xa0', ' ')
        except:
            return None
        data_data = {
            'md5_value': md5_value,
            'source': list_data['content_url'],
            'title': list_data['title'],
            'formulating_authority': '人力资源社会保障部',
            'law_nature': None,
            'timeliness': None,
            'publish_date': list_data['publish_date'],
            'law_category': None,
            'entry_into_force_time': None,
            'announcement_title': list_data['announcement_title'],
            'announcement_url': list_data['announcement_url'],
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
            item_mains['content'] = data_data['content']
            # insert_data(table='law_regulation', data=item_main)
            yield item_mains

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')