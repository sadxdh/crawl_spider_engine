"""产品召回-国家市监总局 → product_recall"""
import hashlib, re, scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *

_C = lambda v: (v[0] if isinstance(v, list) and v else v or '').strip()


class SamrdprcRecallSpider(BaseSpider):
    name = 'economy_recall_samrdprc'
    data_table = 'product_recall'
    allowed_domains = ['samrdprc.org.cn']
    proxy_type = 'long_proxy'
    custom_settings = {'CONCURRENT_REQUESTS': 8, 'DOWNLOAD_DELAY': 0.3}
    dedup_fields = ['md5_value']
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,'
                  'image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Host': 'www.samrdprc.org.cn',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/126.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
    }

    def match_publish_time(self, text):
        match = re.findall(r'发布时间：(\d{4}-\d{2}-\d{2})', text)
        publish_time = match[0] if match else None
        return publish_time

    def start_requests(self):
        for cat in ['qczh/gnzhqc', 'xfpzh/xfpgnzh']:
            for page in range(self.start_page, self.end_page + 1):
                if page == 1:
                    url = f'https://www.samrdprc.org.cn/{cat}/index.html'
                else:
                    url = f'https://www.samrdprc.org.cn/{cat}/index_{page - 1}.html'
                yield scrapy.Request(
                    url=url,
                    headers=self.headers,
                    callback=self.parse_list,
                    errback=self.errback,
                    cb_kwargs={'recall_url': url}
                )

    def parse_list(self, response, recall_url):
        recall_element = etree.HTML(response.text.encode(response.encoding).decode('utf-8'))
        li_list = recall_element.xpath('//div[@class="boxl_ul"]/ul/li')
        for li in li_list:
            details_href = li.xpath('./a/@href')[0]
            details_url = urljoin(recall_url, details_href)
            title = li.xpath('./a/@title')[0].strip()

            if '】' in title:  # 消费品
                company_name_list = re.findall(r'】(.*?).*召回', title)
            else:
                company_name_list = title.split('召回')[0].split('、')
            temp = {'details_url': details_url, 'company_name_list': company_name_list, 'title': title}
            yield scrapy.Request(
                url=details_url,
                headers=self.headers,
                callback=self.parse_detail,
                encoding='utf-8',
                errback=self.errback,
                cb_kwargs={'parms': temp}
            )

    def parse_detail(self, details_responses, parms):
        """xpath解析"""
        details_html = details_responses.body
        details_element = etree.HTML(details_html)
        release_date = details_element.xpath('//div[@class="show_tit2"]/text()')[0]
        release_date = self.match_publish_time(release_date)
        html_node_code = get_node_html(details_responses,
                                       content_xpath='//div[@class="TRS_Editor"]',
                                       rm_node_xpath=['//style'],
                                       replace_src_xpath='//div[@class="TRS_Editor"]/p/span/img'
                                       )
        details_url = parms['details_url']
        company_name_list = parms['company_name_list']
        title = parms['title']
        # 有可能一个标题会出现两个公司, 拆开存, 内容一样
        items = {}
        for company_name in company_name_list:
            md5_value = hash_md5(release_date + company_name + title)
            items['md5_value'] = md5_value
            items['release_date'] = release_date
            items['entity_name'] = company_name
            items['announcement_title'] = title
            items['announcement_url'] = details_url
            items['content'] = html_node_code
            items['source'] = '国家市场监督管理总局'
            self.log_info(items)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
