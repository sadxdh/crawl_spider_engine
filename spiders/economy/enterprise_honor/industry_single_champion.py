import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class IndustrySingleChampionSpider(BaseSpider):
    name = 'enterprise_honor_single_champion'
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
        'Referer': 'http://www.cfie.org.cn/index/work/index/id/19.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    }
    base_url = 'http://www.cfie.org.cn/index/work/li/id/19.html?cid=22'

    def start_requests(self):
        yield scrapy.Request(
            url=self.base_url,
            method='GET',
            headers=self.headers,
            callback=self.parse_list
        )

    def parse_list(self, response):
        result = etree.HTML(response.text)
        rows = xpath_parse(result, '//div[@class="mlist"]/ul/li', return_list=True)
        for row in rows:
            title = xpath_parse(row, './a/text()')
            href = xpath_parse(row, './a/@href')
            detail_url = urljoin(response.url, href)
            temp = {'title': title, 'detail_url': detail_url}
            yield scrapy.Request(
                url=detail_url,
                method='GET',
                headers=self.headers,
                callback=self.parse_detail,
                cb_kwargs={'data': temp}
            )

    def parse_detail(self, response, data):
        result = etree.HTML(response.text)

        release_date = xpath_parse(result, '//div[@class="info_time"]/p/text()').split(' ')[0]
        release_date = dispose_update_date(release_date)
        announcement_title = xpath_parse(result, '//div[contains(@class,"detail-body")]/p/a/@title')
        href = xpath_parse(result, '//div[contains(@class,"detail-body")]/p/a/@href')
        announcement_url = urljoin(response.url, href)

        title = data['title']
        md5_value = hash_md5(title + str(release_date))

        items = {}
        items['md5_value'] = md5_value
        items['honor_name'] = '国家级制造业单项冠军'
        items['theme_class'] = '科技型企业'
        items['title'] = title
        items['company'] = '中国工业经济联合会'
        items['level'] = '国家级'
        items['release_date'] = release_date
        items['release_mechanism'] = '中国工业经济联合会'
        items['announcement_title'] = announcement_title
        items['announcement_url'] = announcement_url
        # insert_data(table='honor_information', data=item)
        yield items


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')