"""
产权交易爬虫
本地调试：scrapy crawl economy_chanquan -a start_page=1 -a end_page=5
"""
import scrapy
from spiders.base_spider import BaseSpider

class ChanquanSpider(BaseSpider):
    name = 'economy_chanquan'
    allowed_domains = ['crei.cn']

    data_table = 'entity_propertyright_transaction'
    dedup_fields = ['url']

    default_end_page = 50

    def start_requests(self):
        for url in self.page_urls('http://www.crei.cn/chanquan/list?page={page}'):
            yield scrapy.Request(url, callback=self.parse_list,
                                 meta={'page': int(url.split('=')[-1])},
                                 errback=self.errback)

    def parse_list(self, response):
        rows = response.css('.item-list .item')
        if not rows:
            self.log_warning(f"第 {response.meta['page']} 页列表为空: {response.url}")
            return

        for row in rows:
            title = row.css('.title::text').get('').strip()
            href = row.css('a::attr(href)').get('')
            pub_date = row.css('.date::text').get('').strip()
            if not title or not href:
                continue
            yield scrapy.Request(
                url=response.urljoin(href),
                callback=self.parse_detail,
                meta={'title': title, 'pub_date': pub_date},
                errback=self.errback,
            )

    def parse_detail(self, response):
        item = {}
        item['project_name'] = response.meta.get('title', '')
        item['file_url'] = response.url
        item['disclose_start_date'] = response.meta.get('pub_date', '')
        item['source'] = '产权交易网'
        item['content'] = ' '.join(response.css('.content *::text').getall()).strip()
        item['transaction_type'] = response.css('.project-type::text').get('').strip()
        item['listing_price'] = response.css('.price::text').get('').strip()
        yield item

    def errback(self, failure):
        self.log_error(f"请求失败: {failure.request.url} - {failure.value}")
