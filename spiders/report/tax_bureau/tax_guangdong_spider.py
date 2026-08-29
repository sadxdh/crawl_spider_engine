"""广东省税务局公告爬虫 → entity_government_announcement
旧项目参照: data_crawl_server guangdong_tax_spider.py
"""
import json, hashlib, scrapy
from lxml import etree, html
from urllib.parse import urljoin, urlparse, urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *


class GuangdongTaxSpider(BaseSpider):
    name = 'report_tax_guangdong'
    # data_table = 'entity_government_announcement'
    dedup_fields = ['md5_value']
    custom_settings = {'CONCURRENT_REQUESTS': 3, 'DOWNLOAD_DELAY': 1}
    proxy_type = "long_proxy"
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,'
                  'image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://guangdong.chinatax.gov.cn/gdsw/tzgg/common_list.shtml',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0',
    }

    website_source = '国家税务总局广东省税务局'

    def generate_params(self, page):
        params = {
            '_pageSize': '15',
            'page': page,
            '_isAgg': 'true',
            '_isJson': 'true',
            '_template': 'index',
            '_rangeTimeGte': '',
            '_channelName': '',
        }
        return params

    def extract_detail(self, response):
        result = response.text
        html_text = html.fromstring(result)
        content = xpath_parse(html_text, '//div[@class="content"]')
        content = html.tostring(content, encoding='unicode')
        return content

    def extract_attachment(self, response):
        result = response.text
        html_text = etree.HTML(result)
        temp_list = []

        rows = html_text.xpath('//td[@id="conntentNR"]/p[(a) and contains(text(), "附件")]/a')
        for row in rows:
            attach_title = row.xpath('./text()')
            attach_href = row.xpath('./@href')
            attach_url = urljoin(response.url, attach_href)
            temp = {'attach_title': attach_title, 'attach_url': attach_url}
            temp_list.append(temp)
        return temp_list

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            params = self.generate_params(page)
            url = "https://guangdong.chinatax.gov.cn/gdtaxejs/common/search/fede883a3ee54f32b7e955a728f4cede?" + urlencode(params)
            yield scrapy.Request(
                url=url,
                method="GET",
                headers=self.headers,
                callback=self.extract_list,
                dont_filter=True,
            )

    def extract_list(self, response):
        domain = extract_domain_protocol(response.url)
        result = response.json()['data']['results']
        for row in result:
            title = row.get('title')
            href = row.get('url')
            url = urljoin(domain, href)
            release_time = row['publishedTimeStr']
            temp = {'title': title, 'url': url, 'release_time': release_time}
            yield scrapy.Request(
                url=url,
                method='GET',
                headers=self.headers,
                callback=self.get_detail,
                cb_kwargs={'data': temp}
            )

    def get_detail(self, response, data):
        announce_title = data['title']
        announce_url = data['url']
        release_time = data['release_time']
        try:
            content = self.extract_detail(response)
            attachment_list = self.extract_attachment(response)
        except Exception as e:
            error_msg = f'url: {announce_url}, {self.website_source}, 公告详情解析错误: {e}'
            self.log_error(error_msg)
            # send_dd_msg(self.spider_name, '解析失败', error_msg)
        else:
            if content:
                md5_value = hash_md5(str(release_time) + announce_title + self.website_source)

                items = {}
                items['publish_time'] = release_time
                items['announcement_title'] = announce_title
                items['announcement_url'] = announce_url
                items['content'] = content
                items['source'] = self.website_source
                items['md5_value'] = md5_value
                items['_table'] = 'entity_government_announcement'
                # insert_data('entity_government_announcement', data=item)
                yield items
                yield from self.save_attach_data(attachment_list, md5_value)

    def save_attach_data(self, attach_list, md5_value):
        """存储附件"""
        for attach in attach_list:
            attach_title = attach['attach_title']
            attach_url = attach['attach_url']
            attach_md5_value = hash_md5(md5_value+attach_title+attach_url)

            items = {}
            items['announcement_md5_value'] = md5_value
            items['attachment_title'] = attach_title
            items['attachment_url'] = attach_url
            items['md5_value'] = attach_md5_value
            items['_table'] = 'entity_government_announcement_mapping'
            # insert_data('entity_government_announcement_mapping', data=item)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
