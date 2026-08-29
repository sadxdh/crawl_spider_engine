import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *
from spiders.economy.yuncrawl_pbc.conf import *
from spiders.economy.yuncrawl_pbc.pcb_webpage import PbcListPage, PcbDetailPage

class EconomyMonitorPcbProvinceSpider(BaseSpider):
    name = 'monitor_pcb_province'
    data_table = 'enterprise_dynamics'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        # "Referer": "https://www.pbc.gov.cn/zhengwugongkai/4081330/4081344/4081407/4081705/index.html",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "sec-ch-ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    @staticmethod
    def generate_url(url, page):
        result = re.sub('index', f'd80f41dc-{page}', url) if page > 1 else url
        return result

    def start_requests(self):
        for conf in confs:
            end_page = self.end_page if self.end_page >= 0 else conf.get('end_page')
            pages = [i for i in range(self.start_page, int(end_page) + 1)]
            web_url = conf.get('url')
            for page in pages:
                url = self.generate_url(web_url, page)
                yield scrapy.Request(
                    url=url,
                    method='GET',
                    headers=self.headers,
                    dont_filter=True,
                    callback=self.parse_list,
                    cb_kwargs={'conf': conf}
                )

    def parse_list(self, response, conf):

        page = PbcListPage(response)
        result = page.parse_list(conf)
        for item in result:
            url = item['url']
            yield scrapy.Request(
                url=url,
                method='GET',
                headers=self.headers,
                callback=self.parse_detail,
                cb_kwargs={'conf': conf,'list_data': item},
            )

    async def parse_detail(self, response, conf, list_data):
        page = PcbDetailPage(response)
        detail_data = await page.parse_detail(conf)

        title = list_data['title']
        release_time = list_data['release_time']

        website_name = conf.get('website_name')

        items = {}
        items['release_time'] = release_time
        items['title'] = title
        items['url'] = list_data['url']
        items['content'] = detail_data['content']
        items['webname'] = website_name
        items['md5_value'] = hash_md5(str(title) + str(release_time) + website_name)
        yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')