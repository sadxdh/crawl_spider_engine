import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class EnterpriseHonorTechIncubatorSpider(BaseSpider):
    name = 'enterprise_honor_tech_incubator'
    data_table = 'honor_information'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;'
                  'q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://www.most.gov.cn/xxgk/xinxifenlei/fdzdgknr/index_5.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    }
    base_url = 'https://znjs.most.gov.cn/search/api/fulltext/searchCondition'

    @staticmethod
    def generate_data(keyword, page):
        data = {
            'searchword': keyword,
            'ssearchword': '',
            'channel': '',
            'group': '全站',
            'keyWords2': '',
            'keyWords3': '',
            'keyWords4': '',
            'timeType': 'all',
            'appendixType': 'all',
            'sortType': '1',
            'position': 'anywhere',
            'dateBegin': '',
            'dateEnd': '',
            'currentPage': page,
        }
        return data

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            for keyword in ['年度国家级科技企业孵化器', '年度国家备案众创空间']:
                data = self.generate_data(keyword, page)
                yield scrapy.FormRequest(
                    url=self.base_url,
                    headers=self.headers,
                    method="POST",
                    formdata=data,
                    callback=self.parse_list,
                    dont_filter=True,
                )

    def parse_list(self, response):
        result = response.json()['result']['list']
        for data in result:
            title_element = etree.HTML(data['title'])
            title = xpath_parse(title_element, '//text()')
            if (title and '科技部' in title and '审核' not in title
                    and ('年度国家级科技企业孵化器' in title or '年度国家备案众创空间' in title)):
                detail_url = data['puburl']
                release_date = data['reltime'].replace('.', '-')
                temp = {'title': title, 'detail_url': detail_url, 'release_date': release_date}
                yield scrapy.Request(
                    url=detail_url,
                    headers=self.headers,
                    method="GET",
                    cb_kwargs={'data': temp},
                    callback=self.parse_detail
                )

    def parse_detail(self, response, data):
        title = data['title']
        release_date = data['release_date']

        result = etree.HTML(response.text.encode(response.encoding).decode('utf-8'))
        info_text = xpath_parse(result, '//div[@id="Zoom"]/p//text()')
        index_number = xpath_parse(result, '//table[@class="bd1"]/tbody/tr[2]/td[2]/text()')
        document_number = xpath_parse(result, '//table[@class="bd1"]/tbody/tr[4]/td[2]/text()')
        announcement_title = xpath_parse(result, '//div[@id="Zoom"]/p/a/text()')
        href = xpath_parse(result, '//div[@id="Zoom"]/p/a/@href')
        announcement_url = urljoin(response.url, href)

        if '年度国家级科技企业孵化器的通知' in title:
            honor_name = '国家级科技孵化器'
        elif '年度国家备案众创空间的通知' in title:
            honor_name = '国家众创空间'
        else:
            honor_name = None

        if not announcement_title:
            announcement_title = title
        md5_value = hash_md5(title + str(release_date) + announcement_title)
        items = {}
        items['md5_value'] = md5_value
        items['honor_name'] = honor_name
        items['title'] = title
        items['company'] = '中华人民共和国科学技术部'
        items['theme_class'] = '科技型企业'
        items['level'] = '国家级'
        items['release_date'] = release_date
        items['index_number'] = index_number
        items['release_mechanism'] = '中华人民共和国科学技术部'
        items['document_number'] = document_number
        items['info_text'] = info_text
        items['announcement_title'] = announcement_title
        items['announcement_url'] = announcement_url
        # insert_data(table='honor_information', data=item)
        yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')