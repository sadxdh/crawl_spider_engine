"""产品召回-上海市监局，来源：https://scjgj.sh.gov.cn/1435 → product_recall"""
import hashlib, re, scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *

_URL = 'https://scjgj.sh.gov.cn/1435'
_H = {'User-Agent': 'Mozilla/5.0'}
_C = lambda v: (v[0] if isinstance(v, list) and v else v or '').strip()


class ShanghaiRecallSpider(BaseSpider):
    name = 'economy_recall_shanghai'
    data_table = 'product_recall'
    allowed_domains = ['scjgj.sh.gov.cn']
    proxy_type = 'long_proxy'
    dedup_fields = ['md5_value']
    custom_settings = {'CONCURRENT_REQUESTS': 8, 'DOWNLOAD_DELAY': 0.3}
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,'
                  'image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://scjgj.sh.gov.cn/1435/index.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0',
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            if page == 1:
                url = f'https://scjgj.sh.gov.cn/1435/index.html'
            else:
                url = f'https://scjgj.sh.gov.cn/1435/index_{page}.html'
            yield scrapy.Request(
                url,
                headers=self.headers,
                callback=self.parse_list,
                errback=self.errback
            )

    def parse_list(self, response):
        result = BeautifulSoup(response.text, 'lxml')
        rows = result.select('.table_list>tr')
        for row in rows:
            if row.a is None:
                continue
            announcement_title = row.a['title']
            announcement_title = announcement_title.split('】')[1] if '】' in announcement_title else announcement_title
            entity_name = match_text(announcement_title, pattern=r'(.*?公司|.*?厂|.*?店|.*?商行|.*?部|.*?鞋业).*召回')

            href = row.a['href']
            announcement_url = urljoin(response.url, href)
            release_date = row.select('td')[-2].text.strip()

            temp = {'announcement_title': announcement_title, 'announcement_url': announcement_url,
                    'release_date': release_date, 'entity_name': entity_name}
            yield scrapy.Request(
                url=announcement_url,
                headers=self.headers,
                callback=self.parse_detail,
                errback=self.errback,
                cb_kwargs={'parms': temp}
            )

    def parse_detail(self, response, parms):
        html_node_code = get_node_html(response,
                                       content_xpath='//*[@class="layui-table"]',
                                       replace_src_xpath='//p//img')

        announcement_title = parms['announcement_title']
        release_date = parms['release_date'].strip()
        entity_name = parms['entity_name']
        items = {}
        if entity_name:
            md5_value = hash_md5(release_date + entity_name + announcement_title)
            items['md5_value'] = md5_value
            items['release_date'] = release_date
            items['entity_name'] = entity_name
            items['announcement_title'] = announcement_title
            items['announcement_url'] = parms['announcement_url']
            items['content'] = html_node_code
            items['source'] = '上海市市场监督管理局'
            self.log_info(items)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')