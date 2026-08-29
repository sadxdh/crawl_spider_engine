"""国家税务总局湖南省税务局公告爬虫 → entity_government_announcement
旧项目参照: data_crawl_server hunan_tax_spider.py
"""
import hashlib, scrapy
from lxml import etree, html
from urllib.parse import urljoin
from spiders.base_spider import BaseSpider
from utils.hunan_chinatax.fake_ruishu import *
from utils.tools import *


class HunanTaxSpider(BaseSpider):
    name = 'report_tax_hunan'
    # data_table = 'entity_government_announcement'
    dedup_fields = ['md5_value']
    custom_settings = {'CONCURRENT_REQUESTS': 3, 'DOWNLOAD_DELAY': 1}

    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "zh-CN,zh;q=0.9",
        "cache-control": "max-age=0",
        "priority": "u=0, i",
        # "referer": "https://hunan.chinatax.gov.cn/lists/20190409002106/1",
        "sec-ch-ua": "\"Google Chrome\";v=\"137\", \"Chromium\";v=\"137\", \"Not/A)Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    }


    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            api_url = f'https://hunan.chinatax.gov.cn/lists/20190409002106/{page}'
            response = fake_rs_request(url=api_url, headers=self.headers)
            yield from self.parse_list(response)

    def parse_list(self, response):
        if response:
            result = response.text.encode(response.encoding).decode('utf-8')
            tree_html = etree.HTML(result)
            xpath_content = '//div[@id="newsRight"]/ul/li[(a)]'
            li_list = xpath_parse(tree_html, xpath_content=xpath_content, return_list=True)
            for li in li_list:
                href = xpath_parse(li, './a/@href')
                url = urljoin(response.url, href)
                title = xpath_parse(li, './a/@title')
                release_time = xpath_parse(li, './a/span[@class="rightdate"]/text()')
                temp = {'url': url, 'title': title, 'release_time': release_time}
                yield from self.get_detail(temp)

    def get_detail(self, data):
        announce_title = data['title']
        announce_url = data['url']
        release_time = data['release_time']
        response = fake_rs_request(url=announce_url, headers=self.headers)
        if response:
            try:
                content = self.parse_detail(response)
                attachment_list = self.parse_attachment(response)
            except Exception as e:
                error_msg = f'url: {announce_url}, 公告详情解析错误: {e}'
                self.log_error(error_msg)
                # send_dd_msg(self.spider_name, '解析失败', error_msg)
            else:
                website_source = '国家税务总局湖南省税务局'
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

    def parse_detail(self, response):
        result = response.text.encode(response.encoding).decode('utf-8')
        html_text = html.fromstring(result)
        content = xpath_parse(html_text, '//div[@class="dynamic-detail__content"]')
        content = html_del_attr_tag(content, del_tag=['//script', '//style'])
        content = html.tostring(content, encoding='unicode')
        return content

    @staticmethod
    def parse_attachment(response):
        result = response.text.encode(response.encoding).decode('utf-8')
        html_text = etree.HTML(result)
        temp_list = []

        rows = html_text.xpath('//div[@class="dynamic-detail__content"]//p[contains(text(),"附件")]/a')
        for row in rows:
            attach_title = row.xpath('./text()')[0]
            attach_href = row.xpath('./@href')[0]
            attach_url = urljoin(response.url, attach_href)

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
