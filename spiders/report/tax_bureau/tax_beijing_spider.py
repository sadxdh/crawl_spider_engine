"""北京市税务局公告爬虫 → entity_government_announcement
旧项目参照: data_crawl_server beijing_tax_spider.py (RsRequest)
"""
import hashlib, scrapy
from lxml import etree, html
from urllib.parse import urljoin
from spiders.base_spider import BaseSpider
from utils.ruishu.rs_crawler import RsRequest
from utils.tools import *


class BeijingTaxSpider(BaseSpider):
    name = 'report_tax_beijing'
    # data_table = 'entity_government_announcement'
    dedup_fields = ['md5_value']
    custom_settings = {'CONCURRENT_REQUESTS': 3, 'DOWNLOAD_DELAY': 1}
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,'
                  'image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0',
    }
    re_reqs = RsRequest()


    def parse_detail(self, response):
        result = response.text.encode(response.encoding).decode('utf-8')
        html_text = html.fromstring(result)
        content = html_text.xpath('//div[@id="xwzx_content_all"]')[0]
        content = html_del_attr_tag(content, del_tag=['//script', '//style'])
        content = html.tostring(content, encoding='unicode')
        return content

    @staticmethod
    def parse_attachment(response):
        result = response.text.encode(response.encoding).decode('utf-8')
        html_text = etree.HTML(result)
        temp_list = []

        rows = html_text.xpath('//div[@class="xwzx_fujian"]/ul/li/a')
        for row in rows:
            attach_title = row.xpath('./text()')[0]
            attach_href = row.xpath('./@href')[0]
            attach_url = urljoin(response.url, attach_href)

            temp = {'attach_title': attach_title, 'attach_url': attach_url}
            temp_list.append(temp)
        return temp_list


    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            if page == 1:
                base_url = 'http://beijing.chinatax.gov.cn/bjswj/c104279/zxfb.shtml'
            else:
                base_url = 'http://beijing.chinatax.gov.cn/bjswj/c104279/zxfb_{}.shtml'.format(page)
            response = self.re_reqs.rs_request(url=base_url, headers=self.headers)
            if response.status_code == 200:
                yield from self.parse_list(response)
            else:
                msg = f'{base_url}，瑞数，国家税务总局北京市税务局，列表页解析错误'
                self.log_error(msg)

    def parse_list(self, response):
        result = response.text.encode(response.encoding).decode('utf-8')
        tree_html = etree.HTML(result)
        xpath_content = '//div[@class="index_zxfb_left"]/ul/li'
        li_list = xpath_parse(tree_html, xpath_content=xpath_content, return_list=True)
        for li in li_list:
            href = xpath_parse(li, './span/a/@href')
            if '.pdf' in href or '.xlsx' in href:
                continue
            url = urljoin(response.url, href)
            title = xpath_parse(li, './span/a/@title')
            release_time = xpath_parse(li, './span[2]/text()')
            yield from self.data_list({'url': url, 'title': title, 'release_time': release_time})

    def data_list(self, data):
        announce_title = data['title']
        announce_url = data['url']
        release_time = data['release_time']
        response = self.re_reqs.rs_request(announce_url, headers=self.headers)
        if response:
            try:
                content = self.parse_detail(response)
                attachment_list = self.parse_attachment(response)
            except Exception as e:
                error_msg = f'url: {announce_url}，瑞数，国家税务总局北京市税务局, 公告详情解析错误'
                self.log_error(error_msg)
            else:
                website_source = '国家税务总局北京市税务局'
                md5_value = hash_md5(str(release_time) + announce_title + website_source)
                # 正文内容保存
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
                # 附件保存
                yield from self.save_attach_data(attachment_list, md5_value)

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
