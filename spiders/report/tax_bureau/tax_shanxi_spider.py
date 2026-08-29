"""国家税务总局山西省税务局公告爬虫 → entity_government_announcement
旧项目参照: data_crawl_server shanxi_tax_spider.py
"""
import hashlib, re, scrapy
from lxml import etree, html
from urllib.parse import urljoin, urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *


class ShanxiTaxSpider(BaseSpider):
    name = 'report_tax_shanxi'
    # data_table = 'entity_government_announcement'
    dedup_fields = ['md5_value']
    custom_settings = {'CONCURRENT_REQUESTS': 3, 'DOWNLOAD_DELAY': 1}

    headers = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/json; charset=UTF-8",
        "Origin": "https://shanxi.chinatax.gov.cn",
        "Referer": "https://shanxi.chinatax.gov.cn/web/list/sx-11400-522",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    domain = 'http://shanxi.chinatax.gov.cn'

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            params = {
                'sqlid': 'web_data_wz2',
                'limit': '15',
                'lmdm': '522',
                'orgid': '11400',
                'ptwz': 'Y',
                'page': 1,
            }

            data = {
                'start': 0 if page == 1 else (page - 1) * 15,
            }
            url = 'http://shanxi.chinatax.gov.cn/common/extQuery'
            url = f"{url}?{urlencode(params)}"
            response = curl_cffi_request(url=url, data=data, headers=self.headers, method="POST", proxies_type=True)
            yield from self.parse_list(response)

    def parse_list(self, response):
        result = response.json()['message']['list']
        for row in result:
            title = row['DETAILTITLE']
            href = row['WZID']
            url = f'http://shanxi.chinatax.gov.cn/web/detail/sx-11400-522-{href}'
            release_time = row['FBSJ']
            temp = {'title': title, 'url': url, 'release_time': release_time}
            yield from self.get_detail(temp)

    def get_detail(self, data):
        announce_title = data['title']
        announce_url = data['url']
        release_time = data['release_time']

        if '.pdf' not in announce_url:
            response = curl_cffi_request(url=announce_url, method="GET", headers=self.headers, proxies_type=True)
            if response:
                try:
                    content = self.parse_detail(response)
                    attachment_list = self.parse_attachment(response)
                except Exception as e:
                    error_msg = f'url: {announce_url}, 公告详情解析错误: {e}'
                    self.log_error(error_msg)
                    # send_dd_msg(self.spider_name, '解析失败', error_msg)
                else:
                    website_source = '国家税务总局山西省税务局'
                    md5_value = hash_md5(str(release_time) + announce_title + website_source)

                    items = {}
                    items['publish_time'] = release_time
                    items['announcement_title'] = announce_title
                    items['announcement_url'] = announce_url
                    items['content'] = content
                    items['source'] = website_source
                    items['md5_value'] = md5_value
                    items['_table'] = 'entity_government_announcement'
                    # insert_data('entity_government_announcement', data=item)
                    yield items

                    yield from self.save_attach_data(attachment_list, md5_value)

    @staticmethod
    def parse_detail(response):
        result = response.text
        html_text = html.fromstring(result)

        content = html_text.xpath('//div[@class="content"]')[0]
        content = html.tostring(content, encoding='unicode')
        return content

    def parse_attachment(self, response):
        result = response.text
        html_text = etree.HTML(result)
        temp_list = []

        rows = html_text.xpath('//div[@id="zoom"]/p[(a) and contains(text(), "附件")]/a')
        for row in rows:
            attach_title = xpath_parse(row, './@title')
            attach_href = xpath_parse(row, './@href')
            attach_url = urljoin(self.domain, attach_href)

            temp = {'attach_title': attach_title, 'attach_url': attach_url}
            temp_list.append(temp)
        return temp_list

    def save_attach_data(self, attach_list, md5_value):
        for attach in attach_list:
            attach_title = attach['attach_title']
            attach_url = attach['attach_url']
            attach_md5_value = hash_md5(md5_value + attach_title + attach_url)

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
