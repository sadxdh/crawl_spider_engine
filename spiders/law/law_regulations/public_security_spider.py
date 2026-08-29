import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class PublicSecuritySpider(BaseSpider):
    name = 'public_security'
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

    base_url = "https://app.mps.gov.cn/searchweb/search_new.jsp#" # 数据来源

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            headers = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer": "https://app.mps.gov.cn/searchweb/search_new.jsp",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
            }

            url = "https://app.mps.gov.cn/searchweb/searchPic"

            data = {
                "sortType": "0",
                "pageSize": "10",
                "pageNow": str(page),
                "fullText": "刑事",
                "searchType": "0",
                "cateId": "",
                "timeRange": "0",
                "keyType": "title",
                "ex": "",
                "lowerLimit": "",
                "upperLimit": "",
                "jsflIndexSeleted": "",
                "highlighter": "2",
                "jsfl": "zcwj",
                "searchScope": "0",
                "keywordNavigation": "0",
            }

            yield scrapy.FormRequest(
                url=url,
                method="POST",
                headers=headers,
                formdata=data,
                callback=self.parse_list,
                dont_filter=True,
            )

    def parse_list(self, response):
        json_data = response.json()
        for li in json_data["array"]:
            content_url = li['url']
            title = li['titleTerm']
            date_str = li['showTime']
            # 切割拼接：年-月-日
            publish_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
            url_list = {
                'title': title,
                'publish_date': publish_date,
                'content_url': content_url
            }
            yield from self.get_content(url_list)

    def get_content(self, list_data):
        url = list_data['content_url'].replace('http:', 'https:')
        response = get_jsl_cookies(url)
        if response:
            data_data = self.content_data(response, list_data)
            yield from self.parse_content(data_data)


    def content_data(self, response, list_data):
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'lxml')
        md5_value = hash_md5(f"{list_data['content_url']}{list_data['title']}")
        content = str(soup.select('#ztdx')[0])
        if soup.select('#ztdx [class="xgwz"]'):
            content = content.replace(str(soup.select('#ztdx [class="xgwz"]')[0]), '')
        content = BeautifulSoup(content, 'lxml').text

        data_data = {
            'md5_value': md5_value,
            'source': list_data['content_url'],
            'title': list_data['title'],
            'formulating_authority': '公安部',
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
        return data_data

    def parse_content(self, data_data):
        item_mains = {}
        # item_main = LawRegulationItem()
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