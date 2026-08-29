"""商标公告 → trademark_info_file_upload
数据来源：sbj.cnipa.gov.cn/sbj/tzgg/
"""
import scrapy
from lxml import etree
from spiders.base_spider import BaseSpider

_HDRS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

class TrademarkSpider(BaseSpider):
    name = 'economy_trademark'
    data_table = 'trademark_info_file_upload'
    dedup_fields = ['announcement_url']
    allowed_domains = ['sbj.cnipa.gov.cn']
    default_end_page = 1

    custom_settings = {
        'CONCURRENT_REQUESTS': 2,
        'DOWNLOAD_DELAY': 1,
        'COOKIES_ENABLED': True,
    }

    def start_requests(self):
        yield scrapy.Request(
            url='https://sbj.cnipa.gov.cn/sbj/tzgg/',
            headers=_HDRS, callback=self._parse_list, errback=self.errback)

    def _parse_list(self, response):
        tree = etree.HTML(response.body)
        for a in tree.xpath('//div[contains(@class,"gts_contentLeftList")]//a[@href]'):
            title = ''.join(a.xpath('.//text()')).strip()
            href = a.get('href', '').strip()
            if not title or not href or len(title) < 5:
                continue
            if './20' in href or '../20' in href:
                yield scrapy.Request(url=response.urljoin(href), headers=_HDRS,
                                     callback=self._parse_detail, errback=self.errback,
                                     meta={'title': title})

    def _parse_detail(self, response):
        title = response.meta['title']
        content = ' '.join(response.xpath('//div[contains(@class,"content")]//text()').getall()).strip()
        if not content:
            content = ' '.join(response.xpath('//body//text()').getall()).strip()[:5000]

        item = {'announcement_title': title[:300], 'announcement_url': response.url}
        yield item

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
