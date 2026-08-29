"""司法部-行政许可/处罚 → enterprise_dynamics"""
import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *


class MojSuperviseSpider(BaseSpider):
    name = 'economy_moj_supervise'
    data_table = 'enterprise_dynamics'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 5, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
            'middlewares.curl_cffi_middleware.CurlCffiMiddleware': 520,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "sec-ch-ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    @staticmethod
    def generate_url(url, page):
        result = re.sub('index', f'index_{page - 1}', url) if page > 1 else url
        return result

    def start_requests(self):
        url_list = {
            '行政许可': 'https://www.moj.gov.cn/pub/sfbgw/zwxxgk/fdzdgknr/fdzdgknrxzxk/index.html',
            '行政处罚': 'https://www.moj.gov.cn/pub/sfbgw/zwxxgk/fdzdgknr/fdzdgknrcfqz/index.html',
        }

        for channel, url in url_list.items():
            for page in range(self.start_page, self.end_page + 1):
                url = self.generate_url(url, page)
                yield scrapy.Request(
                    url=url,
                    headers=self.headers,
                    method="GET",
                    callback=self.parse_list
                )

    def parse_list(self, response):
        rows = response.xpath('//ul[@class="listCont"]/li')
        for row in rows:
            title = row.xpath('./a/p/text()').get()
            url = row.xpath('./a/@href').get()
            release_time = row.xpath('./span[@class="time"]/text()').get()

            temp = {'title': title, 'url': url, 'release_time': release_time}
            yield scrapy.Request(
                url=url,
                headers=self.headers,
                method="GET",
                callback=self.parse_detail,
                cb_kwargs={'data': temp}
            )

    def parse_detail(self, response, data):
        date_str = response.xpath('//p[@class="ly"]/text()').get()
        release_time = date_str.split('发布时间：')[1].strip()
        release_time = release_time if release_time else data['release_time']

        content = response.xpath('//div[@class="TRS_Editor"]/p/text()').getall()
        content = ''.join(content)
        website_name = '中华人民共和国司法部'

        items = {}
        items['release_time'] = release_time
        items['title'] = data['title']
        items['url'] = data['url']
        items['content'] = content
        items['webname'] = website_name
        items['md5_value'] = hash_md5(data['title'] + release_time + website_name)
        yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
