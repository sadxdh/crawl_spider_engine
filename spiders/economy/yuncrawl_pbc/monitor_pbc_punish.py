import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *


class EconomyMonitorPbcPunishSpider(BaseSpider):
    name = 'monitor_pbc_punish'
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
        url_list = {
            '行政处罚': 'https://www.pbc.gov.cn/zhengwugongkai/4081330/4081344/4081407/4081705/index.html'
        }

        for channel, url in url_list.items():
            for page in range(self.start_page, self.end_page + 1):
                url = self.generate_url(url, page)
                yield scrapy.Request(
                    url=url,
                    method='GET',
                    headers=self.headers,
                    dont_filter=True,
                    callback=self.parse,
                )

    def parse(self, response):
        rows = response.xpath('//ul[@class="txtlist"]/li')
        for row in rows:
            title = row.xpath('./a/@title').get()
            href = row.xpath('./a/@href').get()
            url = response.urljoin(href)
            release_time = row.xpath('./span[@class="date"]/text()').get()

            temp = {'title': title, 'url': url, 'release_time': release_time}
            yield scrapy.Request(
                url=url,
                method='GET',
                headers=self.headers,
                callback=self.parse_detail,
                cb_kwargs={'data': temp}
            )

    def parse_detail(self, response, data):
        try:
            table = response.xpath('//div[@id="easysiteText"]/table')
            contents = self.extract_html_table(table)
            content = '，'.join(contents)
        except:
            content = response.xpath('//div[@class="TRS_Editor"]/p/text()').getall()
            content = ''.join(content)

        release_time = data['release_time']
        website_name = '中国人民银行'

        items = {}
        items['release_time'] = release_time
        items['title'] = data['title']
        items['url'] = data['url']
        items['content'] = content
        items['webname'] = website_name
        items['md5_value'] = hash_md5(data['title'] + release_time + content + website_name)
        yield items

    def extract_html_table(self, table, header=True):
        """解析 HTML 中的 table，按行转为 字符串字典 格式"""
        if not table:
            return []

        trs = table[0].xpath('.//tr')
        if not trs:
            return []

        result = []

        # 处理表头
        headers = trs.pop(0).xpath('.//td') if header else []
        # 处理每一行
        for tr in trs:
            tds = tr.xpath('.//td')

            rows = []
            for k, v in zip(headers, tds):
                k = k.xpath('.//text()').getall()
                v = v.xpath('.//text()').getall()
                row = f"{''.join(k)}:{''.join(v)}"
                rows.append(row)
            row_str = '，'.join(rows)

            result.append(row_str)

        return result

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
