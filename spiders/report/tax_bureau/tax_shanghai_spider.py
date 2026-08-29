"""上海市税务局公告爬虫 → entity_government_announcement
旧项目参照: data_crawl_server sh_tax_spider.py
"""
import hashlib, re, scrapy
from lxml import etree, html
from urllib.parse import urljoin
from spiders.base_spider import BaseSpider
from utils.tools import *


class ShanghaiTaxSpider(BaseSpider):
    name = 'report_tax_shanghai'
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
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,'
                  '*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://shanghai.chinatax.gov.cn/xxgk/tzgg/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0',
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            if page == 1:
                url = 'https://shanghai.chinatax.gov.cn/xxgk/tzgg/index.html'
            else:
                url = f'https://shanghai.chinatax.gov.cn/xxgk/tzgg/index_{page - 1}.html'
            yield scrapy.Request(
                url=url,
                method='GET',
                headers=self.headers,
                callback=self.parse_list,
                cb_kwargs={'times': 1}
            )

    def parse_list(self, response, times):
        result = response.text.encode(response.encoding).decode('utf-8')
        html_text = etree.HTML(result)
        xpath_dict = {1: '//ul[@class="infolist"]/li', 2: '//ul/li', 3: '//ul[@class="subst_content"]/li'}
        xpath_str = xpath_dict[times]
        rows = html_text.xpath(xpath_str)
        for row in rows:
            title = row.xpath('./a/@title')[0]
            href = row.xpath('./a/@href')[0]
            url = urljoin(response.url, href)
            temp = {'title': title, 'url': url}
            self.log_info(f'{response.url}, 列表解析结果:{temp}')
            if times == 1:
                if '纳税申报催报公告' in title or '纳税申报催缴公告' in title:
                    yield scrapy.Request(
                        url=url,
                        method='GET',
                        headers=self.headers,
                        callback=self.parse_list,
                        cb_kwargs={'times': 2}
                    )
                else:
                    yield scrapy.Request(
                        url=url,
                        method='GET',
                        headers=self.headers,
                        callback=self.get_detail_text,
                        cb_kwargs={'data': temp}
                    )
            else:
                if '.htm' in href:
                    yield scrapy.Request(
                        url=url,
                        method='GET',
                        headers=self.headers,
                        callback=self.get_detail_text,
                        cb_kwargs={'data': temp}
                    )
                else:
                    yield scrapy.Request(
                        url=url,
                        method='GET',
                        headers=self.headers,
                        callback=self.parse_list,
                        cb_kwargs={'times': 3}
                    )


    def get_detail_text(self,response, data):
        url = data['url']
        title = data['title']
        if '100dudian' in url or 't472467' in url or 't468329' in url:
            pass
        else:
            if response:
                try:
                    content, release_time = self.parse_detail_text(response)
                    attach_list = self.parse_attachment(response)
                except Exception as e:
                    error_msg = f'url: {url}, 文本详情解析错误, e:{e}'
                    self.log_error(error_msg)
                    # send_dd_msg(self.spider_name, '解析失败', error_msg)
                else:
                    website_source = '国家税务总局上海市税务局'
                    md5_value = hash_md5(str(release_time) + title + website_source)

                    items = {}
                    items['publish_time'] = release_time
                    items['announcement_title'] = title
                    items['announcement_url'] = url
                    items['content'] = content
                    items['source'] = website_source
                    items['md5_value'] = md5_value
                    items['_table'] = 'entity_government_announcement'
                    # insert_data('entity_government_announcement', data=item)
                    yield items
                    yield from self.save_attach_data(attach_list, md5_value)

    @staticmethod
    def parse_detail_text(response):
        result = response.text.encode(response.encoding).decode('utf-8')
        html_text = html.fromstring(result)
        content = html_text.xpath('//div[@id="ivs_content"]')[0]
        content = html.tostring(content, encoding='unicode')
        time_res = html_text.xpath('//span[@id="ivs_date"]/text()')
        if time_res:
            release_time = time_res[0]
        else:
            time_str = html_text.xpath('//span[@class="time js_time"]/text()')[0]
            release_time = time_str.split('：')[1]
        return content, release_time

    @staticmethod
    def parse_attachment(response):
        result = response.text.encode(response.encoding).decode('utf-8')
        result = re.findall(r'fileName=(.*?);', result)
        temp_list = []
        if result:
            result = etree.HTML(result[0])
            attach_list = result.xpath('//a')
            for item in attach_list:
                href = item.xpath('./@href')[0]
                url = urljoin(response.url, href)
                title = item.xpath('./text()')[0]

                attach_md5_value = hash_md5(title + url)
                temp = {'title': title, 'url': url, 'attach_md5_value': attach_md5_value}
                temp_list.append(temp)
        return temp_list

    def save_attach_data(self, attach_list, md5_value):
        for attach in attach_list:
            attach_md5_value = attach['attach_md5_value']
            attach_title = attach['title']
            attach_url = attach['url']

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
