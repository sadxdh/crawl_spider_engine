"""
企业荣誉爬虫（honor_information）
数据来源：多个政府官网，覆盖 7 类荣誉认定

荣誉类型：
  1. 高新技术企业         innocom.gov.cn
  2. 国家级制造业单项冠军  cfie.org.cn
  3. 国家企业技术中心      ndrc.gov.cn
  4. 国家技术创新示范企业  miit.gov.cn
  5. 科技型中小企业        ctp.gov.cn（暂未实现，该站异步加载）
  6. 知识产权示范/优势企业 cnipa.gov.cn（POST+详情）
  7. 国家级科技孵化器/众创空间 znjs.most.gov.cn

增量策略：
  start_page=1 end_page=2（取各源最新2页）
  去重字段：md5_value（title + release_date + announcement_title 的 md5，
            无附件时 announcement_title=title）

本地调试：
  scrapy crawl economy_honor_information -a start_page=1 -a end_page=2
"""
import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *

class EnterpriseHonorHighTechSpider(BaseSpider):
    """企业荣誉爬虫（多源合并）"""
    name = 'enterprise_honor_high_tech'
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
        'Host': 'www.innocom.gov.cn',
        'Referer': 'http://www.innocom.gov.cn/gqrdw/c101334/list_gsgg_l2.shtml',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/127.0.0.0 Safari/537.36',
    }

    @staticmethod
    def generate_url(page):
        base_url = 'http://www.innocom.gov.cn/gqrdw/c101481/list_gsgg_l2{}.shtml'
        return base_url.format(f'_{page}') if page > 1 else base_url.format('')

    # ------------------------------------------------------------------ #
    # start_requests                                                       #
    # ------------------------------------------------------------------ #
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
        result = etree.HTML(response.body)
        rows = xpath_parse(result, '//ul[@class="list"]/li', return_list=True)
        for row in rows:
            release_date = xpath_parse(row, './span/text()')
            title = xpath_parse(row, './a/text()')
            href = xpath_parse(row, './a/@href')
            detail_url = urljoin(response.url, href)
            temp = {'title': title, 'detail_url': detail_url, 'release_date': release_date}
            yield scrapy.Request(
                url=detail_url,
                method='GET',
                headers=self.headers,
                callback=self.parse_detail,
                cb_kwargs={'data': temp}
            )

    def parse_detail(self, response, data):
        result = etree.HTML(response.body)
        text_xpath_list = [
            '//div[@id="content"]//p//text()',
            '//div[@id="detailContent"]//p//text()',
        ]
        title_xpath_list = [
            '//div[@id="detailContent"]/a/text()',
            '//div[@id="content"]//p//a/text()',
            '//div[@id="detailContent"]//p//a/text()',
        ]
        href_xpath_list = [
            '//div[@id="detailContent"]/a/@href',
            '//div[@id="content"]//p//a/@href',
            '//div[@id="detailContent"]//p//a/@href',
        ]

        info_text = xpath_parse(result, ' | '.join(text_xpath_list))
        announcement_title = xpath_parse(result, ' | '.join(title_xpath_list))
        href = xpath_parse(result, ' | '.join(href_xpath_list))

        announcement_url = urljoin(response.url, href)

        title = data['title']
        release_date = data['release_date']

        md5_value = hash_md5(title+release_date)
        items = {}
        items['md5_value'] = md5_value
        items['title'] = title
        items['honor_name'] = '高新技术企业'
        items['company'] = '高新技术企业认定管理工作网'
        items['level'] = '国家级'
        items['release_date'] = release_date
        items['theme_class'] = '科技型企业'
        items['release_mechanism'] = '高新技术企业'
        items['info_text'] = info_text
        items['announcement_title'] = announcement_title
        items['announcement_url'] = announcement_url
        # insert_data(table='honor_information', data=item)
        yield items


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
