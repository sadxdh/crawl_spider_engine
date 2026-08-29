"""市监局-行政处罚 → enterprise_dynamics"""
from urllib.parse import urlencode

import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *


class SamrPunishSpider(BaseSpider):
    name = 'economy_samr_punish'
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
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "If-Modified-Since": "Tue, 30 Jun 2026 03:23:32 GMT",
        "If-None-Match": "W/\"6a4336b4-176be\"",
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
    def generate_params(page):
        params = {
            'webId': '29e9522dc89d4e088a953d8cede72f4c',
            'pageId': '17b480e9786f4327b56375c311795bf3',
            'parseType': 'bulidstatic',
            'pageType': 'column',
            'tagId': '内容区域',
            'tplSetId': '5c30fb89ae5e48b9aefe3cdf49853830',
            'paramJson': '{"pageNo":%s,"pageSize":20}' % str(page),
        }
        return params

    def start_requests(self):
        url = 'https://www.samr.gov.cn/api-gateway/jpaas-publish-server/front/page/build/unit'
        for page in range(self.start_page, self.end_page + 1):
            params = self.generate_params(page)
            request_url = f"{url}?{urlencode(params)}"

            yield scrapy.Request(
                url=request_url,
                method="GET",
                headers=self.headers,
                dont_filter=True,
                callback=self.parse,
            )

    def parse(self, response):
        result = response.json()
        html_str = result['data']['html']
        soup = BeautifulSoup(html_str, 'lxml')
        rows = soup.select('.Three_zhnlist_02>ul')
        for row in rows:
            title = row.a['title']
            href = row.a['href']
            detail_url = response.urljoin(href)
            meta_data = {'title': title, 'detail_url': detail_url}

            if title:
                yield scrapy.Request(
                    detail_url,
                    dont_filter=True,
                    callback=self.parse_detail,
                    method="GET",
                    headers=self.headers,
                    cb_kwargs={'data': meta_data}
                )

    def parse_detail(self, response, data):

        release_time = response.xpath('//li[@class="Three_xilan_04"]/text()').get()
        release_time = re_parse(release_time, r'发布时间：(\d{4}-\d{2}-\d{2} \d{2}:\d{2})')
        content = response.xpath('//div[@id="zoom"]//p//text()').getall()
        content = ''.join(content)

        title = data['title']
        website_name = '国家市场监督管理总局'

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
