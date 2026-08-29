import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *


class EnterpriseHonorTmsSpider(BaseSpider):
    name = 'enterprise_honor_tms'
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
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,'
                  'image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'http://www.ctp.gov.cn/zxqyfw/gsgg/gsgglist_23.shtml',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    }

    @staticmethod
    def generate_url(page):
        base_url = 'http://www.ctp.gov.cn/zxqyfw/gsgg/gsgglist{}.shtml'
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
        result = etree.HTML(response.text)
        rows = xpath_parse(result, '//ul[@class="list_con"]/li', return_list=True)
        for row in rows:
            release_date = xpath_parse(row, './span[@class="list_time"]/text()')
            title = xpath_parse(row, './a/text()')
            href = xpath_parse(row, './a/@href')
            detail_url = urljoin(response.url, href)
            temp = {
                'release_date': release_date,
                'title': title,
                'detail_url': detail_url
            }
            yield scrapy.Request(
                url=detail_url,
                method='GET',
                headers=self.headers,
                cb_kwargs={'data': temp},
                callback=self.parse_detail,
            )

    def parse_detail(self, response, data):
        result = etree.HTML(response.text)

        announcement_title = xpath_parse(result, '//div[@class="fjjian"]/p/a/text()')
        href = xpath_parse(result, '//div[@class="fjjian"]/p/a/@href')
        announcement_url = urljoin(response.url, href)

        title = data['title']
        release_date = data['release_date']
        md5_value = hash_md5(title+str(release_date))

        items = {}
        items['md5_value'] = md5_value
        items['honor_name'] = '科技型中小企业'
        items['title'] = title
        items['theme_class'] = '科技型企业'
        items['company'] = '中华人民共和国工业和信息化部'
        items['level'] = '国家级'
        items['release_date'] = release_date
        items['release_mechanism'] = '中华人民共和国工业和信息化部'
        items['announcement_title'] = announcement_title
        items['announcement_url'] = announcement_url
        # insert_data(table='honor_information', data=item)
        yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
