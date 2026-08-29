"""国家税务总局大连市税务局公告爬虫 → entity_government_announcement
旧项目参照: data_crawl_server dalian_tax_spider.py
"""
import hashlib, re, scrapy
from urllib.parse import urljoin, urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *

class DalianTaxSpider(BaseSpider):
    name = 'report_tax_dalian'
    # data_table = 'entity_government_announcement'
    dedup_fields = ['md5_value']
    custom_settings = {'CONCURRENT_REQUESTS': 3, 'DOWNLOAD_DELAY': 1}
    proxy_type = "long_proxy"
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,'
                  'image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0',
    }
    website_source = '国家税务总局大连市税务局'

    def generate_params(self, page):
        start = 1 if page == 1 else (page - 1) * 45 + 1
        end = 45 if start == 1 else start + 44
        params = {'startrecord': start, 'endrecord': end, 'perpage': '15'}
        return params

    def generate_data(self):
        data = {
            'col': '1',
            'webid': '2',
            'path': 'http://dalian.chinatax.gov.cn/',
            'columnid': '1715',
            'sourceContentType': '1',
            'unitid': '16477',
            'webname': '国家税务总局大连市税务局',
            'permissiontype': '0',
        }
        return data

    def extract_detail(self, response):
        result = response.text.encode(response.encoding).decode('utf-8')
        html_text = html.fromstring(result)
        content = xpath_parse(html_text, '//div[@id="zoom"]')
        content = html_del_attr_tag(content, del_tag=['//script', '//style'])
        content = html.tostring(content, encoding='unicode')
        return content

    def extract_attachment(self, response):
        result = response.text.encode(response.encoding).decode('utf-8')
        html_text = etree.HTML(result)
        temp_list = []

        rows = html_text.xpath('//div[@id="zoom"]/p[(a) and contains(text(), "附件")]/a[(text())]')
        for row in rows:
            attach_title = xpath_parse(row, './text()')
            attach_href = xpath_parse(row, './@href')
            attach_url = urljoin(response.url, attach_href)

            temp = {'attach_title': attach_title, 'attach_url': attach_url}
            temp_list.append(temp)
        return temp_list

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            params = self.generate_params(page)
            data = self.generate_data()
            url = "https://dalian.chinatax.gov.cn/module/web/jpage/dataproxy.jsp?" + urlencode(params)

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
                title = row.xpath('.//a/text()')[0].strip()
                href = row.xpath('.//a/@href')[0].strip().replace('http:', 'https:')
                release_time = xpath_parse(row, './/span/text()')
                domain = extract_domain_protocol(response.url)
                url = urljoin(domain, href)
                temp = {'title': title, 'url': url, 'release_time': release_time}
                yield scrapy.Request(
                    url=url,
                    method='GET',
                    headers=self.headers,
                    errback=self.log_error,
                    callback=self.get_detail,
                    cb_kwargs={'data': temp}
                )

    def get_detail(self, response, data):
        announce_title = data['title']
        announce_url = data['url']
        release_time = data['release_time']
        soup = BeautifulSoup(response.text, 'lxml')
        try:
            content = self.extract_detail(response)
            attachment_list = self.extract_attachment(response)
            announce_title = soup.select('[id="title"]')[0].text.strip()
        except Exception as e:
            error_msg = f'url: {announce_url}, 国家税务总局大连市税务局, 公告详情解析错误: {e}'
            self.log_info(error_msg)
        else:
            if content:
                md5_value = hash_md5(str(release_time) + announce_title + self.website_source)
                # 正文内容保存
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
