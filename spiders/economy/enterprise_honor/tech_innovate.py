import scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *

class EnterpriseHonorTechInnovateSpider(BaseSpider):
    name = 'enterprise_honor_tech_innovate'
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
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://www.miit.gov.cn/gyhxxhb/jgsj/kjs/wzpz/ztzl/gjjscxsfqy/tzgg/index.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    }
    base_url = 'https://www.miit.gov.cn/api-gateway/jpaas-publish-server/front/page/build/unit'

    @staticmethod
    def generate_params(page):
        params = {
            'webId': '8d828e408d90447786ddbe128d495e9e',
            'pageId': '2b0835611b9743618e889ace8fd088e9',
            'parseType': 'buildstatic',
            'pageType': 'column',
            'tagId': '信息列表',
            'tplSetId': '209741b2109044b5b7695700b2bec37e',
            'paramJson': '{"pageNo":%s,"pageSize":"15"}' % page,
        }
        return params

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            params = self.generate_params(page)
            separator = "&" if "?" in self.base_url else "?"
            request_url = f"{self.base_url}{separator}{urlencode(params)}"
            yield scrapy.Request(
                url=request_url,
                method="GET",
                headers=self.headers,
                callback=self.parse_list,
                dont_filter=True,
            )

    def parse_list(self, response):
        html_str = response.json()['data']['html']
        result = etree.HTML(html_str)
        rows = xpath_parse(result, '//div[@class="page-content"]/table/tbody/tr', return_list=True)
        for row in rows:
            title = xpath_parse(row, './td[2]/a/text()')
            href = xpath_parse(row, './td[2]/a/@href')
            detail_url = urljoin(response.url, href)
            temp = {'title': title, 'detail_url': detail_url}
            yield scrapy.Request(
                url=detail_url,
                method="GET",
                headers=self.headers,
                callback=self.parse_detail,
                cb_kwargs={'data': temp},
            )

    def parse_detail(self, response, data):
        title = data['title']

        result = etree.HTML(response.text)
        base_xpath = '//table[@class="yyl_center"]/tbody/tr/td/table/tbody/tr[2]/td/table/tbody/tr/td/table{}'
        date_and_origin = xpath_parse(result, base_xpath.format('[2]/tbody/tr/td/text()'))
        release_date = match_text(date_and_origin)
        release_mechanism = date_and_origin.split('信息来源：')[1]
        info_text = xpath_parse(result, base_xpath.format('[3]/tbody/tr/td//text()'))
        document_number = match_text(info_text, '(工信部.*?号)')
        rows = xpath_parse(result, base_xpath.format('[3]/tbody/tr/td//a'), return_list=True)
        if rows is not None:
            for row in rows:
                announcement_title = xpath_parse(row, './text()')
                href = xpath_parse(row, './@href')
                announcement_url = urljoin(response.url, href)
                if not announcement_title:
                    continue

                md5_value = hash_md5(title + str(release_date) + announcement_title)
                items = {}
                items['md5_value'] = md5_value
                items['honor_name'] = '国家技术创新示范企业'
                items['title'] = title
                items['company'] = '中华人民共和国工业和信息化部'
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