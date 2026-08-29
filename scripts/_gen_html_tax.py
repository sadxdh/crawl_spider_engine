"""生成 GET HTML 模式的税局蜘蛛"""
import os

NEW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'spiders', 'report', 'tax_bureau')

# 每个省的配置: (filename, class, spider_name, url_template, source, list_xpath, title_xpath, href_xpath, date_xpath, detail_xpath, attach_xpath)
CONFIGS = [
    ('tax_guangxi_spider.py', 'GuangxiTaxSpider', 'report_tax_guangxi',
     "https://guangxi.chinatax.gov.cn/xxgk/tzgg/index{}.html",
     '国家税务总局广西省税务局',
     "//div[@class='lmy_info']/ul/li[(a)]", './a/text()', './a/@href', './span/text()',
     "//div[@class='m-c-text']",
     "//ul[@class='downfile']/li"),

    ('tax_guizhou_spider.py', 'GuizhouTaxSpider', 'report_tax_guizhou',
     "https://guizhou.chinatax.gov.cn/xxgk/tzgg/index{}.html",
     '国家税务总局贵州省税务局',
     "//div[@class='NewsList']/ul/li", './a/@title', './a/@href', './span/text()',
     "//div[@id='Zoom']/div[last()]/preceding-sibling::div",
     "//div[@id='Zoom']//p/a"),

    ('tax_hainan_spider.py', 'HainanTaxSpider', 'report_tax_hainan',
     "https://hainan.chinatax.gov.cn/ssxc_1_5/index{}.html",
     '国家税务总局海南省税务局',
     "//div[@class='nrlb1-r-t-x']/ul/li", './a/text()', './a/@href', './em/text()',
     "//div[@class='zx-xxxqy-nr'] | //div[@id='img-content']",
     "//div[contains(@class,'fujian')]/ul/ul/li"),

    ('tax_hebei_spider.py', 'HebeiTaxSpider', 'report_tax_hebei',
     "http://hebei.chinatax.gov.cn/hbsw/xxgk/tzgg/index{}.html",
     '国家税务总局河北省税务局',
     "//div[@class='lefbarbig']/ul/li", './a/text()', './a/@href', './span/text()',
     "//div[@class='TRS_Editor'] | //div[@id='fontzoom']",
     "//div[@id='download']/table//tr/td[a]"),
]


TPL = '''"""{source}公告爬虫 → entity_government_announcement
旧项目参照: data_crawl_server {key}_tax_spider.py
"""
import hashlib, scrapy
from lxml import etree, html
from urllib.parse import urljoin
from spiders.base_spider import BaseSpider

_URL_TPL = '{url_template}'
_SOURCE = '{source}'
_LIST_XPATH = "{list_xpath}"
_DETAIL_XPATH = "{detail_xpath}"
_ATTACH_XPATH = "{attach_xpath}"

_H = {{
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36',
}}


class {class_name}(BaseSpider):
    name = '{spider_name}'
    data_table = 'entity_government_announcement'
    dedup_fields = ['md5_value']
    custom_settings = {{'CONCURRENT_REQUESTS': 3, 'DOWNLOAD_DELAY': 1}}

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            url = _URL_TPL.format('') if page == 1 else _URL_TPL.format(f'_{{page}}')
            yield scrapy.Request(url=url, headers=_H, callback=self._parse_list, errback=self.errback)

    def _parse_list(self, response):
        try:
            tree = etree.HTML(response.text)
        except Exception:
            return
        rows = tree.xpath(_LIST_XPATH)
        for row in rows:
            title = ''.join(row.xpath('{title_xpath}')).strip()
            href = ''.join(row.xpath('{href_xpath}')).strip()
            release_time = ''.join(row.xpath('{date_xpath}')).strip()
            if not title:
                continue
            url = urljoin(response.url, href)
            md5 = hashlib.md5((str(release_time) + title + _SOURCE).encode()).hexdigest()
            yield scrapy.Request(
                url=url, callback=self._parse_detail, errback=self.errback,
                headers=_H, meta={{'title': title, 'release_time': release_time, 'url': url, 'md5_value': md5}},
            )

    def _parse_detail(self, response):
        meta = response.meta
        try:
            tree = etree.HTML(response.text)
        except Exception:
            tree = None

        content = ''
        if tree is not None:
            try:
                cn = tree.xpath(_DETAIL_XPATH)
                if cn:
                    for bad in cn[0].xpath('.//script|.//style'):
                        p = bad.getparent()
                        if p is not None:
                            p.remove(bad)
                    content = etree.tostring(cn[0], encoding='unicode')
            except Exception:
                pass

        attachment_title = ''
        attachment_url = ''
        if tree is not None:
            try:
                atts = tree.xpath(_ATTACH_XPATH)
                titles = [''.join(a.xpath('./a/text()|./text()')).strip() for a in atts]
                hrefs = [''.join(a.xpath('./a/@href|./@href')).strip() for a in atts]
                attachment_title = ','.join(t for t in titles if t) if any(titles) else ''
                attachment_url = ','.join(response.urljoin(h) for h in hrefs if h) if any(hrefs) else ''
            except Exception:
                pass

        yield {{
            'publish_time': meta['release_time'], 'announcement_title': meta['title'],
            'announcement_url': meta['url'], 'source': _SOURCE,
            'announcement_type': '', 'abstract': '', 'content': content, 'emotion': '',
            'md5_value': meta['md5_value'], '_table': 'entity_government_announcement',
        }}

    def errback(self, failure):
        self.log_error(f'请求失败: {{failure.request.url}} — {{failure.value}}')
'''

for cfg in CONFIGS:
    (fname, class_name, spider_name, url_tpl, source,
     list_xpath, title_xpath, href_xpath, date_xpath,
     detail_xpath, attach_xpath) = cfg
    key = fname.replace('tax_', '').replace('_spider.py', '')
    code = TPL.format(
        key=key, class_name=class_name, spider_name=spider_name,
        url_template=url_tpl, source=source,
        list_xpath=list_xpath, title_xpath=title_xpath,
        href_xpath=href_xpath, date_xpath=date_xpath,
        detail_xpath=detail_xpath, attach_xpath=attach_xpath,
    )
    with open(os.path.join(NEW, fname), 'w', encoding='utf-8') as f:
        f.write(code)
    print(f'  OK  {fname}  [{source}]')

print(f'\nGenerated: {len(CONFIGS)}')
