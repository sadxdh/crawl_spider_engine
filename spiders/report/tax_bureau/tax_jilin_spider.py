"""国家税务总局吉林省税务局公告爬虫 → entity_government_announcement
旧项目参照: data_crawl_server jilin_tax_spider.py
"""
import hashlib, scrapy
from spiders.base_spider import BaseSpider
from utils.ruishu.rs_crawler import RsRequest
from utils.tools import *



class JilinTaxSpider(BaseSpider):
    name = 'report_tax_jilin'
    # data_table = 'entity_government_announcement'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        # 'DOWNLOADER_MIDDLEWARES': {
        #     'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        # }
    }
    # proxy_type = "long_proxy"
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,'
                  'image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'http://jilin.chinatax.gov.cn/col/col404/index.html?uid=16050&pageNum=3',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0',
    }

    re_reqs = RsRequest()
    website_source = '国家税务总局吉林省税务局'

    @staticmethod
    def generate_url(page):
        base_url = 'http://jilin.chinatax.gov.cn/col/col404/index.html?uid=16050&pageNum={}'.format(page)
        return base_url

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            api_url = self.generate_url(page)
            response = self.re_reqs.rs_request(api_url, headers=self.headers)
            try:
                yield from self.parse_list(response)
            except Exception as e:
                msg = f'url: {api_url}，瑞数，{self.website_source}， 列表页解析错误, e:{e}'
                self.log_error(msg)
                # send_dd_msg(self.spider_name, '解析失败', msg)

    def parse_list(self, response):
        domain = extract_domain_protocol(response.url)
        response = response.text.encode(response.encoding).decode('utf-8')
        result = etree.HTML(response)
        result = xpath_parse(result, '//script[@type="text/xml"]/text()')
        html_text = re.findall('<recordset>(.*?)</recordset>', result.replace('\n', ''))
        if html_text:
            li_text = re.findall('<li.*?>(.*?)</li>', html_text[0])
            for row in li_text:
                row = etree.HTML(row)
                title = xpath_parse(row, './/a/text()')
                href = xpath_parse(row, './/a/@href')
                release_time = xpath_parse(row, './/span/text()')
                url = urljoin(domain, href)
                temp = {'title': title, 'url': url, 'release_time': release_time}
                yield from self.get_detail(temp)

    def get_detail(self, data):
        announce_title = data['title']
        announce_url = data['url']
        release_time = data['release_time']
        response = self.re_reqs.rs_request(announce_url, headers=self.headers)
        if response:
            try:
                content = self.parse_detail(response)
                attachment_list = self.parse_attachment(response)
            except Exception as e:
                error_msg = f'url: {announce_url}, 瑞数, {self.website_source}, 公告详情解析错误: {e}'
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
                yield items
                # insert_data('entity_government_announcement', data=item)
                yield from self.save_attach_data(attachment_list, md5_value)

    def parse_detail(self, response):
        result = response.text.encode(response.encoding).decode('utf-8')
        html_text = html.fromstring(result)
        content = xpath_parse(html_text, '//div[@id="zoom"] | //div[@id="img-content"]')
        if content:
            content = html_del_attr_tag(content, del_tag=['//script', '//style'])
            content = html.tostring(content, encoding='unicode')
        return content

    @staticmethod
    def parse_attachment(response):
        result = response.text.encode(response.encoding).decode('utf-8')
        html_text = etree.HTML(result)
        temp_list = []

        rows = html_text.xpath('//div[@id="zoom"]/p[a]/a')
        for row in rows:
            attach_title = xpath_parse(row, './text()')
            attach_href = xpath_parse(row, './@href')
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
