import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *


class NationEnterpriseCenterSpider(BaseSpider):
    name = 'enterprise_honor_netc'
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
        'Referer': 'https://www.ndrc.gov.cn/xwdt/tzgg/index_1.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    }

    @staticmethod
    def generate_url(page):
        base_url = 'https://www.ndrc.gov.cn/xwdt/tzgg/index{}.html'
        return base_url.format(f'_{page}') if page > 1 else base_url.format('')

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            url = self.generate_url(page)
            yield scrapy.Request(
                url=url,
                method='GET',
                headers=self.headers,
                callback=self.parse_list,
            )

    def parse_list(self, response):
        result = etree.HTML(response.text.encode(response.encoding).decode('utf-8'))
        rows = xpath_parse(result, '//ul[@class="u-list"]/li', return_list=True)
        for row in rows:
            title = xpath_parse(row, './a/@title')
            if title and '国家企业技术中心名单' in title:
                href = xpath_parse(row, './a/@href')
                detail_url = urljoin(response.url, href)
                release_date = xpath_parse(row, './span/text()')
                temp = {'title': title, 'detail_url': detail_url, 'release_date': release_date}
                yield scrapy.Request(
                    url=detail_url,
                    method='GET',
                    headers=self.headers,
                    callback=self.parse_detail,
                    cb_kwargs={'data': temp}
                )

    def parse_detail(self, response, data):
        result = etree.HTML(response.text.encode(response.encoding).decode('utf-8'))
        info_text = xpath_parse(result, '//div[@class="TRS_Editor"]/span/text()')
        document_number = xpath_parse(result, '//div[@class="TRS_Editor"]/span/div/text()')
        release_mechanism = xpath_parse(result, '//div[@class="ly laiyuantext"]/span/text()')

        title = data['title']
        release_date = data['release_date']

        rows = xpath_parse(result, '//div[@class="attachment_r"]/p/a', return_list=True)
        for row in rows:
            announcement_title = xpath_parse(row, './text()')
            if '.pdf' in announcement_title:
                href = xpath_parse(row, './@href')
                announcement_url = urljoin(response.url, href)

                md5_value = hash_md5(title + str(release_date) + announcement_title)
                items = {}
                items['md5_value'] = md5_value
                items['honor_name'] = '国家企业技术中心'
                items['title'] = title
                items['company'] = '中华人民共和国国家发展和改革委员会'
                items['theme_class'] = '科技型企业'
                items['level'] = '国家级'
                items['release_date'] = release_date
                items['release_mechanism'] = release_mechanism
                items['document_number'] = document_number
                items['info_text'] = info_text
                items['announcement_title'] = announcement_title
                items['announcement_url'] = announcement_url
                # insert_data(table='honor_information', data=item)
                yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
