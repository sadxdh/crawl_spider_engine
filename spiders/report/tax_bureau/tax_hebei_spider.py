"""国家税务总局河北省税务局公告爬虫 → entity_government_announcement
旧项目参照: data_crawl_server hebei_tax_spider.py
"""
import hashlib, scrapy
from lxml import etree, html
from urllib.parse import urljoin
from spiders.base_spider import BaseSpider
from utils.tools import *



class HebeiTaxSpider(BaseSpider):
    name = 'report_tax_hebei'
    # data_table = 'entity_government_announcement'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 3, 'DOWNLOAD_DELAY': 1,
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

    website_source = '国家税务总局河北省税务局'

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            url = 'http://hebei.chinatax.gov.cn/hbsw/xxgk/tzgg/index{}.html'
            url = url.format('') if page == 1 else url.format(f'_{page}')
            yield scrapy.Request(
                url=url,
                method='GET',
                headers=self.headers,
                callback=self.extract_list
            )

    def extract_list(self, response):
        temp_list = []
        result = response.text.encode(response.encoding).decode('utf-8')
        result = etree.HTML(result)
        rows = xpath_parse(result, '//div[@class="lefbarbig"]/ul/li', return_list=True)
        for row in rows:
            title = xpath_parse(row, './a/text()')
            href = xpath_parse(row, './a/@href')
            url = urljoin(response.url, href)
            release_time = xpath_parse(row, './span/text()')
            temp = {'title': title, 'url': url, 'release_time': release_time}
            yield scrapy.Request(
                url=url,
                method='GET',
                headers=self.headers,
                callback=self.get_detail,
                cb_kwargs={'data': temp}
            )

    def extract_detail(self, response):
        result = response.text.encode(response.encoding).decode('utf-8')
        html_text = html.fromstring(result)
        content = xpath_parse(html_text, '//div[@class="TRS_Editor"] | //div[@id="fontzoom"]')
        content = html_del_attr_tag(content, del_tag=['//script', '//style'])
        content = html.tostring(content, encoding='unicode')
        return content

    def extract_attachment(self, response):
        result = response.text.encode(response.encoding).decode('utf-8')
        html_text = etree.HTML(result)
        temp_list = []

        rows = html_text.xpath('//div[@id="download"]/table//tr/td[a]')
        for row in rows:
            attach_title = xpath_parse(row, './text()')
            attach_href = xpath_parse(row, './@href')
            attach_url = urljoin(response.url, attach_href)
            if attach_title and attach_href:
                temp = {'attach_title': attach_title, 'attach_url': attach_url}
                temp_list.append(temp)
        return temp_list

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
