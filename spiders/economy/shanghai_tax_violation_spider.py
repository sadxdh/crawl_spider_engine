"""上海税务-重大税收违法 → entity_tax_violation_sh"""
import hashlib, re, scrapy
from lxml import etree
from spiders.base_spider import BaseSpider

_HDRS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36'}

def _md5(*parts):
    return hashlib.md5(''.join(str(p or '') for p in parts).encode()).hexdigest()


class ShanghaiTaxViolationSpider(BaseSpider):
    name = 'economy_shanghai_tax_violation'
    data_table = 'enterprise_dynamics'
    dedup_fields = ['md5_value']
    allowed_domains = ['shanghai.chinatax.gov.cn']
    default_end_page = 3

    def start_requests(self):
        # 旧项目 sh_tax_spider 使用 xxgk/tzgg/ 而非 wzcx/tzgg/
        for page in range(self.start_page, self.end_page + 1):
            url = 'https://shanghai.chinatax.gov.cn/xxgk/tzgg/index.html'
            if page > 1:
                url = f'https://shanghai.chinatax.gov.cn/xxgk/tzgg/index_{page}.html'
            yield scrapy.Request(url=url, headers=_HDRS, callback=self._parse_list, errback=self.errback)

    def _parse_list(self, response):
        tree = etree.HTML(response.body)
        for row in tree.xpath('//ul[@class="infolist"]/li'):
            title = ''.join(row.xpath('./a/@title')).strip()
            href = ''.join(row.xpath('./a/@href')).strip()
            if not title or not href:
                continue
            yield scrapy.Request(url=response.urljoin(href), headers=_HDRS, callback=self._parse_detail, errback=self.errback, meta={'title': title})

    def _parse_detail(self, response):
        tree = etree.HTML(response.body)
        title = response.meta['title']
        content = ''.join(tree.xpath('//div[@id="ivs_content"]//text()')).strip()
        if not content:
            content = ' '.join(tree.xpath('//body//text()').getall()).strip()[:5000]
        # 发布时间
        date_str = ''.join(tree.xpath('//span[@id="ivs_date"]/text()')).strip()
        if not date_str:
            m = re.search(r'(\d{4}-\d{2}-\d{2})', content[:500] if content else '')
            if m: date_str = m.group(1)

        item = {'title': title[:300], 'url': response.url, 'content': content[:5000] if content else '', 'release_time': date_str, 'webname': '国家税务总局上海市税务局', 'md5_value': _md5(title + date_str + '国家税务总局上海市税务局')}
        yield item

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
