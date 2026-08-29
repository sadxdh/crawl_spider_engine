import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class SupremePeopleSpider(BaseSpider):
    name = 'supreme_people'
    data_table = 'law_regulation'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 4, 'DOWNLOAD_DELAY': 1,
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
        # 司法解释
        {'url': 'https://www.court.gov.cn/fabu/gengduo/16.html', 'page': 20},
        # 司法文件
        {'url': 'https://www.court.gov.cn/fabu/gengduo/17.html', 'page': 20},
        # 刑事审判
        {'url': 'https://www.court.gov.cn/shenpan/gengduo/62.html', 'page': 10},
        # 民事审判
        {'url': 'https://www.court.gov.cn/shenpan/gengduo/63.html', 'page': 15},
        # 司法解释
        {'url': 'https://www.spp.gov.cn/spp/sfjs/index.shtml', 'page': 3},
    ]

    def start_requests(self):
        for base_data in self.start_urls:
            all_page = self.end_page if int(self.end_page) > 1 else int(base_data['page'])
            for page in range(self.start_page, all_page + 1):
                base_url = base_data['url']
                yield from self.get_list(page, base_url)


    def get_list(self, page, base_url):
        if 'www.court.gov.cn' in base_url:
            if page != 1:
                base_url = re.sub(r'\.html', f'_{page}.html', base_url)
            response = common_request(url=base_url, headers=self.headers, proxies_type=True)
        elif 'www.spp.gov.cn' in base_url:
            if page != 1:
                base_url = re.sub(r'\.shtml', f'_{page}.shtml', base_url)
            response = common_request(base_url, headers=self.headers, proxies_type=True)
        if response:
            yield from self.parse_list(response, base_url)

    def parse_list(self, response, base_url):
        if 'www.court.gov.cn' in base_url:
            soup = BeautifulSoup(response.text, 'lxml')
            for li in soup.select('.sec_list>ul>li'):
                content_url = urljoin(base_url, li.a['href'])
                if 'https://www.court.gov.cn/fabu/gengduo/16' in base_url:
                    title = li.a['title']
                else:
                    title = li.a['title']
                    # 去除特殊符号，只保留中文、英文、数字
                    clean_title = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', title)
                    if clean_title.endswith(("规定", "意见", "解释")) is False:
                        self.log_error(f'{self.name} 数据被过滤, 标题不是以规定、意见、解释结尾：, url: {content_url}')
                        continue
                publish_date = li.select('.date')[0].text.strip()
                url_list={
                    'title': title,
                    'publish_date': publish_date,
                    'content_url': content_url
                }
                yield from self.get_content(url_list)
        elif 'www.spp.gov.cn' in base_url:
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            for li in soup.select('.commonList_con>ul>li'):
                content_url = urljoin(base_url, li.a['href'])
                title = li.select('a')[0].text.strip()
                publish_date = li.select('span')[0].text.strip()
                url_list = {
                    'title': title,
                    'publish_date': publish_date,
                    'content_url': content_url
                }
                yield from self.get_content(url_list)

    def get_content(self, list_data):
        url = list_data['content_url']
        response = common_request(url, headers=self.headers, proxies_type=True)
        if response:
            data_data = self.content_data(response, list_data)
            yield from self.parse_content(data_data)

    def content_data(self, response, list_data):
        if 'www.court.gov.cn' in list_data['content_url']:
            soup = BeautifulSoup(response.text, 'lxml')
            md5_value = hash_md5(f"{list_data['content_url']}{list_data['title']}")
            if '来源：' in soup.select('[class="clearfix fl message"]>li')[0].text.strip():
                formulating_authority = soup.select('[class="clearfix fl message"]>li')[0].text.strip().replace('来源：', '')
                formulating_authority = None if formulating_authority.strip() == '-' else formulating_authority
            else:
                formulating_authority = None
            content = str(soup.select('[class="txt big"]')[0].text)
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
                'announcement_title': None,
                'announcement_url': None,
                'oss_url': None,
                'content': content
            }
        elif 'www.spp.gov.cn' in list_data['content_url']:
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            md5_value = hash_md5(f"{list_data['content_url']}{list_data['title']}")
            content = soup.select('#fontzoom')[0]
            try:
                h2_title = soup.select('#fontzoom>h2')[0]
                time = soup.select('#fontzoom>.time')[0]
                content = str(content).replace(str(h2_title), '').replace(str(time), '')
                content = BeautifulSoup(content, 'lxml').text
            except:
                content = content.text
            data_data = {
                'md5_value': md5_value,
                'source': list_data['content_url'],
                'title': list_data['title'],
                'formulating_authority': '最高人民法院 最高人民检察院',
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