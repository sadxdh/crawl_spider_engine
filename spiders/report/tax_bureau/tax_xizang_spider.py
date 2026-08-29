"""国家税务总局西藏自治区税务局公告爬虫 → entity_government_announcement
旧项目参照: data_crawl_server xizang_tax_spider.py
"""
import hashlib, re, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *


class XizangTaxSpider(BaseSpider):
    name = 'report_tax_xizang'
    # data_table = 'entity_government_announcement'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = "long_proxy"
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,'
                  'image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0',
    }

    url = 'https://xizang.chinatax.gov.cn/module/web/jpage/dataproxy.jsp'
    website_source = '国家税务总局西藏税务局'

    @staticmethod
    def generate_params(page):
        start = 1 if page == 1 else (page - 1) * 72 + 1
        end = 72 if start == 1 else start + 71
        params = {'startrecord': start, 'endrecord': end, 'perpage': '24'}
        return params

    @staticmethod
    def generate_data():
        data = {
            'col': '1',
            'appid': '1',
            'webid': '1',
            'path': '/',
            'columnid': '5513',
            'sourceContentType': '1',
            'unitid': '13090',
            'webname': '国家税务总局西藏自治区税务局',
            'permissiontype': '0',
        }
        return data

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            params = self.generate_params(page)
            data = self.generate_data()
            url = f"{self.url}?{urlencode(params)}"
            yield scrapy.FormRequest(
                url=url,
                method="POST",
                headers=self.headers,
                formdata=data,
                callback=self.extract_list,
                dont_filter=True,
            )

    def extract_list(self, response):
        result = response.text.encode(response.encoding).decode('utf-8')
        html_text = re.findall('<recordset>(.*?)</recordset>', result.replace('\n', ''))
        if html_text:
            li_text = re.findall('<li.*?>(.*?)</li>', html_text[0])
            for row in li_text:
                row = etree.HTML(row)
                title = xpath_parse(row, './/a/@title')
                href = xpath_parse(row, './/a/@href')
                release_time = xpath_parse(row, './/span/text()')
                domain = extract_domain_protocol(response.url)
                url = urljoin(domain, href)
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
        if response:
            try:
                content, release_time = self.extract_detail(response)
                attachment_list = self.extract_attachment(response)
            except Exception as e:
                error_msg = f'url: {announce_url}, 公告详情解析错误: {e}'
                self.log_error(error_msg)
                # send_dd_msg(self.spider_name, '解析失败', error_msg)
            else:
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

    @staticmethod
    def match_publish_time(text):
        if text is None:
            return None
        match = re.findall(r'发布时间：(\d{4}-\d{2}-\d{2} \d{2}:\d{2})', text)
        publish_time = match[0] if match else None
        return publish_time

    def extract_detail(self, response):
        result = response.text.encode(response.encoding).decode('utf-8')
        html_text = html.fromstring(result)
        time_str = xpath_parse(html_text, '//div[@class="main_content"]/span[1]/text()')
        release_time = self.match_publish_time(time_str)
        content = xpath_parse(html_text, '//div[@id="zoom"]')
        if content:
            content = html_del_attr_tag(content, del_tag=['//script', '//style'])
            content = html.tostring(content, encoding='unicode')
        return content, release_time

    def extract_attachment(self, response):
        result = response.text.encode(response.encoding).decode('utf-8')
        html_text = etree.HTML(result)
        temp_list = []

        rows = html_text.xpath('//div[@id="zoom"]//span[(a)]')
        for row in rows:
            attach_title = xpath_parse(row, './text()')
            attach_href = xpath_parse(row, './@href')
            attach_url = urljoin(response.url, attach_href)
            if attach_title and attach_href:
                temp = {'attach_title': attach_title, 'attach_url': attach_url}
                temp_list.append(temp)
        return temp_list

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
