"""生成 Henan/Shenzhen/Tianjin - 特殊 URL 格式"""
import os
NEW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'spiders', 'report', 'tax_bureau')

CONFIGS = [
    # Henan: UUID page URL
    ('tax_henan_spider.py', 'HenanTaxSpider', 'report_tax_henan', 'henan',
     '国家税务总局河南省税务局',
     "https://henan.chinatax.gov.cn/henanchinatax/xxgk/tzgg/d043c99e-{page}.html",
     'GET_CUSTOM',  # special URL construction
     '//ul[@class="listCon"]/li', './a/text()', './a/@href', './span/text()',
     "//div[@id='mainText']",
     "//div[@id='mainText']/div/p/a"),

    # Shenzhen: .shtml format
    ('tax_shenzhen_spider.py', 'ShenzhenTaxSpider', 'report_tax_shenzhen', 'shenzhen',
     '国家税务总局深圳市税务局',
     "https://shenzhen.chinatax.gov.cn/sztax/xxgk/tzgg/common_list{page}.shtml",
     'GET_PAGE_FMT',
     "//div[@class='pageList infoList listContent']//li/h4", './a/text()', './a/@href', './span/text()',
     "//div[@class='content']",
     "//div[@class='content']//p[font]//a"),

    # Tianjin: POST form
    ('tax_tianjin_spider.py', 'TianjinTaxSpider', 'report_tax_tianjin', 'tianjin',
     '国家税务总局天津市税务局',
     "https://tianjin.chinatax.gov.cn/u_zlmViewMx.action",
     'POST_FORM',
     "//div[@id='main']/table/tr", './td[(a)]/a/@title', './td[(a)]/a/@href', './td[3]/text()',
     "//td[@id='conntentNR']",
     "//td[@id='conntentNR']/p[contains(text(), '附件')]/a"),
]

# Henan specific template
HENAN_TPL = '''"""{source}公告爬虫 → entity_government_announcement
旧项目参照: data_crawl_server {key}_tax_spider.py
"""
import hashlib, scrapy
from lxml import etree, html
from urllib.parse import urljoin
from spiders.base_spider import BaseSpider

_URL_TPL = '{url_template}'
_SOURCE = '{source}'
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
            url = _URL_TPL.format(page=page)
            yield scrapy.Request(url=url, headers=_H, callback=self._parse_list, errback=self.errback)

    def _parse_list(self, response):
        try:
            tree = etree.HTML(response.text)
        except Exception:
            return
        rows = tree.xpath('{list_xpath}')
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
                titles = [''.join(a.xpath('./text()')).strip() for a in atts]
                hrefs = [''.join(a.xpath('./@href')).strip() for a in atts]
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

# Shenzhen template (page format: '' for page 1, '_{page}' otherwise)
SZ_TPL = '''"""{source}公告爬虫 → entity_government_announcement
旧项目参照: data_crawl_server {key}_tax_spider.py
"""
import hashlib, scrapy
from lxml import etree, html
from urllib.parse import urljoin
from spiders.base_spider import BaseSpider

_URL_TPL = '{url_template}'
_SOURCE = '{source}'
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
            pg = '' if page == 1 else f'_{{page}}'
            url = _URL_TPL.format(page=pg)
            yield scrapy.Request(url=url, headers=_H, callback=self._parse_list, errback=self.errback)

    def _parse_list(self, response):
        try:
            tree = etree.HTML(response.text)
        except Exception:
            return
        rows = tree.xpath('{list_xpath}')
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
                titles = [''.join(a.xpath('./text()')).strip() for a in atts]
                hrefs = [''.join(a.xpath('./@href')).strip() for a in atts]
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

# Tianjin POST form template
TJ_TPL = '''"""{source}公告爬虫 → entity_government_announcement
旧项目参照: data_crawl_server {key}_tax_spider.py
"""
import hashlib, scrapy
from lxml import etree, html
from urllib.parse import urljoin
from spiders.base_spider import BaseSpider

_URL = '{url_template}'
_SOURCE = '{source}'
_DETAIL_XPATH = "{detail_xpath}"
_ATTACH_XPATH = "{attach_xpath}"

_H = {{
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Content-Type': 'application/x-www-form-urlencoded',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36',
}}


class {class_name}(BaseSpider):
    name = '{spider_name}'
    data_table = 'entity_government_announcement'
    dedup_fields = ['md5_value']
    custom_settings = {{'CONCURRENT_REQUESTS': 3, 'DOWNLOAD_DELAY': 1}}

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            yield scrapy.FormRequest(
                url=_URL, method='POST', headers=_H,
                formdata={{'lmdm': '010003', 'fjdm': '11200000000', 'page': str(page), 'd': ''}},
                callback=self._parse_list, errback=self.errback,
            )

    def _parse_list(self, response):
        try:
            tree = etree.HTML(response.text)
        except Exception:
            return
        rows = tree.xpath('{list_xpath}')
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
                    content = etree.tostring(cn[0], encoding='unicode')
            except Exception:
                pass
        attachment_title = ''
        attachment_url = ''
        if tree is not None:
            try:
                atts = tree.xpath(_ATTACH_XPATH)
                titles = [a.xpath('./text()')[0] for a in atts if a.xpath('./text()')]
                hrefs = [a.xpath('./@href')[0] for a in atts if a.xpath('./@href')]
                attachment_title = ','.join(titles) if titles else ''
                attachment_url = ','.join(response.urljoin(h) for h in hrefs) if hrefs else ''
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
    fname, class_name, spider_name, key, source, url_tpl, url_type, \
        lx, tx, hx, dx, detail_xpath, attach_xpath = cfg

    if key == 'henan':
        code = HENAN_TPL.format(key=key,class_name=class_name,spider_name=spider_name,source=source,url_template=url_tpl,list_xpath=lx,title_xpath=tx,href_xpath=hx,date_xpath=dx,detail_xpath=detail_xpath,attach_xpath=attach_xpath)
    elif key == 'shenzhen':
        code = SZ_TPL.format(key=key,class_name=class_name,spider_name=spider_name,source=source,url_template=url_tpl,list_xpath=lx,title_xpath=tx,href_xpath=hx,date_xpath=dx,detail_xpath=detail_xpath,attach_xpath=attach_xpath)
    else:
        code = TJ_TPL.format(key=key,class_name=class_name,spider_name=spider_name,source=source,url_template=url_tpl,list_xpath=lx,title_xpath=tx,href_xpath=hx,date_xpath=dx,detail_xpath=detail_xpath,attach_xpath=attach_xpath)

    with open(os.path.join(NEW, fname), 'w', encoding='utf-8') as f:
        f.write(code)
    print(f'  OK  {fname}  [{source}]')
