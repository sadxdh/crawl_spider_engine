"""产品召回-四川省监局，来源：https://scjgj.sc.gov.cn/scjgj/c104536/xxgk_list.shtml → product_recall"""
import hashlib, re, scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *

_URL = 'https://scjgj.sc.gov.cn/scjgj/c104536/xxgk_list.shtml'
_C = lambda v: (v[0] if isinstance(v, list) and v else v or '').strip()


class SichuanRecallSpider(BaseSpider):
    name = 'economy_recall_sichuan'
    data_table = 'product_recall'
    allowed_domains = ['scjgj.sc.gov.cn']
    proxy_type = 'long_proxy'
    dedup_fields = ['md5_value']
    custom_settings = {'CONCURRENT_REQUESTS': 8, 'DOWNLOAD_DELAY': 0.3}
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;'
                  'q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://scjgj.sc.gov.cn/scsjgj/c101376/list.shtml',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            if page == 1:
                url = 'https://scjgj.sc.gov.cn/scsjgj/c101376/list.shtml'
            else:
                url = f'https://scjgj.sc.gov.cn/scsjgj/c101376/list_{page}.shtml'
            yield scrapy.Request(
                url,
                headers=self.headers,
                callback=self.parse_list,
                errback=self.errback
            )

    def parse_list(self, response):
        result = etree.HTML(response.text.encode(response.encoding).decode('utf-8'))
        rows = result.xpath('//div[@class="infolist ymd res split5n"]/ul/li')
        for row in rows:
            announcement_title = row.xpath('./a/text()')[0]
            href = row.xpath('./a/@href')
            announcement_url = urljoin(response.url, href[0])
            release_date = row.xpath('./span/text()')[0]
            if '关于' not in announcement_title and '通告' in announcement_title:
                continue

            temp = {'announcement_url': announcement_url, 'release_date': release_date}
            yield scrapy.Request(
                url=announcement_url,
                headers=self.headers,
                callback=self.parse_detail,
                errback=self.errback,
                cb_kwargs={'parms': temp}
            )
    def parse_detail(self, response, parms):
        html_node_code = get_node_html(response,
                                       content_xpath='//div[@class="article-content"]',
                                       replace_src_xpath='//p/img')
        soup = BeautifulSoup(response.text, 'lxml')
        announcement_title = soup.select('.article-title')[0].text.strip()
        release_date = parms['release_date'].strip()
        entity_name = match_text(announcement_title, pattern=r'关于(.*?公司|.*?厂|.*?店|.*?加工坊).*召回')
        entity_name = entity_name.split('】')[1] if entity_name and '】' in entity_name else entity_name
        items = {}
        if entity_name:
            md5_value = hash_md5(release_date + entity_name + announcement_title)
            items['md5_value'] = md5_value
            items['release_date'] = release_date
            items['entity_name'] = entity_name
            items['announcement_title'] = announcement_title
            items['announcement_url'] = parms['announcement_url']
            items['content'] = html_node_code
            items['source'] = '四川省市场监督管理局'
            self.log_info(items)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
