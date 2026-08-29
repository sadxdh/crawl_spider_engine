"""
中债资信（ChineseCredit）信用评级爬虫
数据来源：https://www.chinaratings.com.cn
列表：https://www.chinaratings.com.cn/CreditRating/RatingInfo/{rating_type}%.html
详情：每家主体 → 逐页翻页抓附件

评级类型：
  ActiveRating=在评  IndustryCommerical=产业商业  FinancialRating=金融

增量策略：
  - 每类前 N 页
  - 增量：start_page=1 end_page=3
  - 去重字段：md5_value（entity_name + rating_date 的 md5）

本地调试：
  scrapy crawl economy_chinese_credit_rating -a start_page=1 -a end_page=3
"""

import scrapy
from spiders.base_spider import BaseSpider
from utils.mysql_tools import select_data
from utils.tools import *


class ChineseCreditRatingSpider(BaseSpider):
    """中债资信信用评级爬虫"""
    name = 'economy_chinese_credit_rating'
    data_table = 'entity_credit_rating'
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
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/126.0.0.0 Safari/537.36',
    }
    rating_type = {'ActiveRating': 74, 'IndustryCommerical': 3, 'FinancialRating': 4}

    @staticmethod
    def generate_list_url(rating_type, page):
        base_url = f'https://www.chinaratings.com.cn/CreditRating/RatingInfo/{rating_type}%3F'
        url = base_url + '.html' if page == 1 else base_url + f'&page={page}.html'
        return url

    def start_requests(self):
        for rating_type, default_pages in self.rating_type.items():
            crawl_pages = default_pages if self.end_page < 0 else self.end_page
            for page in range(self.start_page, int(crawl_pages) + 1):
                url = self.generate_list_url(rating_type, page)
                yield scrapy.Request(
                    url=url,
                    headers=self.headers,
                    callback=self.parse_list
                )

    def parse_list(self, response):
        result = etree.HTML(response.body)
        tr_data_list = xpath_parse(result, '//div[@class="zqliebiao"]/table/tr[(td)]', return_list=True)
        for tr_data in tr_data_list:
            entity_name = xpath_parse(tr_data, './td/a/text()')
            href = xpath_parse(tr_data, './td/a/@href')
            detail_url = urljoin(response.url, href)
            yield from self.list_data({'detail_url': detail_url, 'entity_name': entity_name}, page=1)

    def list_data(self, data, page):
        detail_url = data['detail_url']
        entity_name = data['entity_name']
        url = detail_url if page == 1 else detail_url.replace('.html', f'&page={page}.html')
        yield scrapy.Request(
            url=url,
            headers=self.headers,
            callback=self.parse_detail,
            cb_kwargs={'entity_name': entity_name, 'data': data, 'page': page}
        )

    def parse_detail(self, response, entity_name, data, page):
        result = etree.HTML(response.body)
        tr_data_list = xpath_parse(result, '//div[@class="zqliebiao"]/table/tr[td]', return_list=True)
        if tr_data_list:
            for tr_data in tr_data_list:
                href = xpath_parse(tr_data, './td/a/@href')
                attach_url = urljoin(response.url, href)
                project_name = xpath_parse(tr_data, './td/a/text()')
                rating_date = xpath_parse(tr_data, './td[5]/text()')
                entity_rating = xpath_parse(tr_data, './td[2]/text()')
                rating_outlook = xpath_parse(tr_data, './td[3]/text()')
                mysql_result = select_data(table='wentao_basedata.entity_info',
                                           data=['entity_id'],
                                           condition=f'entity_name = "{entity_name}";')
                entity_id = mysql_result[0]['entity_id'] if mysql_result else None
                url = response.url

                md5_value = hash_md5(entity_name + str(rating_date))
                items = {}
                items['md5_value'] = md5_value
                items['entity_id'] = entity_id
                items['entity_name'] = entity_name
                items['project_name'] = project_name
                items['rating_date'] = rating_date
                items['entity_rating'] = entity_rating
                items['rating_outlook'] = rating_outlook
                items['rating_agency'] = '中债资信评估有限责任公司'
                items['url'] = url
                items['announcement_title'] = entity_name
                yield from self.download_file(attach_url, items)

        if tr_data_list and len(tr_data_list) >= 5 and page < 20:
            page += 1
            yield from self.list_data(data, page)

    def download_file(self, attach_url, items):
        yield scrapy.Request(
            url=attach_url,
            headers=self.headers,
            callback=self.download_item,
            cb_kwargs={'items': items},
            meta={
                'handle_httpstatus_all': True,
            },
        )

    def download_item(self, response, items):
        if response.status == 200:
            ori_url = match_text(response.text, '.*?iframe id="vie_id" src=".*?#(.*?)" width=', placeholder=',')
            origin_pdf_url = ori_url.split(',')[0]
            pdf_url = f'https://www.chinaratings.com.cn{origin_pdf_url}.pdf'
        else:
            pdf_url = None

        items['announcement_url'] = pdf_url
        # insert_data(table='entity_credit_rating', data=item)
        yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
