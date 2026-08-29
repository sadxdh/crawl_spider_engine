"""药监局-药品/器械/化妆品 → enterprise_dynamics"""
import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.ruishu.rs_crawler import RsRequest



class NmpaSuperviseSpider(BaseSpider):
    name = 'economy_nmpa_supervise'
    data_table = 'enterprise_dynamics'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    default_origin_header = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/122.0.0.0 Safari/537.36",
    }
    rs_reqs = RsRequest()

    @staticmethod
    def generate_url(url, page):
        result = re.sub('index', f'index_{page - 1}', url) if page > 1 else url
        return result

    def start_requests(self):

        url_list = {
            '药品监管工作': 'https://www.nmpa.gov.cn/yaopin/ypjgdt/index.html',
            '药品公告通告': 'https://www.nmpa.gov.cn/yaopin/ypggtg/index.html',

            '医疗器械监管工作': 'https://www.nmpa.gov.cn/ylqx/ylqxjgdt/index.html',
            '医疗器械公告通告': 'https://www.nmpa.gov.cn/ylqx/ylqxggtg/index.html',
            '医疗器械飞行检查': 'https://www.nmpa.gov.cn/xxgk/fxjzh/ylqxfxjch/index.html',
            '医疗器械召回': 'https://www.nmpa.gov.cn/xxgk/chpzhh/ylqxzhh/index.html',

            '化妆品监管工作': 'https://www.nmpa.gov.cn/hzhp/hzhpjgdt/index.html',
            '化妆品公告通告': 'https://www.nmpa.gov.cn/hzhp/hzhpjmtg/index.html',
            '化妆品飞行检查': 'https://www.nmpa.gov.cn/hzhp/hzhpcjgg/index.html',
            '化妆品召回': 'https://www.nmpa.gov.cn/xxgk/fxjzh/hzhpfxjch/index.html',
        }
        for channel, url in url_list.items():
            for page in range(self.start_page, self.end_page + 1):
                url = self.generate_url(url, page)
                # yield scrapy.Request(
                #     url=url,
                #     method='GET',
                #     headers=self.default_origin_header,
                #     dont_filter=True,
                #     callback=self.parse,
                # )
                response_rs = self.rs_reqs.rs_request(url=url, headers=self.default_origin_header)
                yield from self.parse(response_rs)

    def parse(self, response):
        rows = response.xpath('//div[@class="list"]/ul/li')
        for row in rows:
            title = row.xpath('./a/text()').get()
            href = row.xpath('./a/@href').get()
            detail_url = response.urljoin(href)
            meta_data = {'title': title, 'detail_url': detail_url}

            # yield scrapy.Request(
            #     detail_url,
            #     headers=self.default_origin_header,
            #     dont_filter=True,
            #     callback=self.parse_detail,
            #     cb_kwargs={'data': meta_data}
            # )
            response_rs = self.rs_reqs.rs_request(url=detail_url, headers=self.default_origin_header)
            yield from self.parse(response_rs, meta_data)

    def parse_detail(self, response, data):

        content = response.xpath('//div[@class="text"]/p//text()').getall()
        content = ''.join(content)
        release_date = response.xpath('//div[@class="date"]/text()').getall()
        release_date = ''.join(release_date)
        release_time = re_parse(release_date, r'(\d{4}-\d{2}-\d{2})')

        title = data['title']
        website_name = '国家药品监督管理局'

        items = {}
        items['release_time'] = release_time
        items['title'] = data['title']
        items['url'] = data['detail_url']
        items['content'] = content
        items['webname'] = website_name
        items['md5_value'] = hash_md5(title + release_time + website_name)
        yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
