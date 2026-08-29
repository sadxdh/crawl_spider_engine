"""批量生成剩余税局蜘蛛 - 混合模式"""
import os, re
OLD = r'C:\Users\24613\workstation\data_crawl_server\spider\report\gov_report\tax_bureau'
NEW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'spiders', 'report', 'tax_bureau')

# 剩余省份配置
REMAINING = {
    'hunan': ('tax_hunan_spider.py', 'HunanTaxSpider', 'report_tax_hunan'),
    'jilin': ('tax_jilin_spider.py', 'JilinTaxSpider', 'report_tax_jilin'),
    'shandong': ('tax_shandong_spider.py', 'ShandongTaxSpider', 'report_tax_shandong'),
    'qingdao': ('tax_qingdao_spider.py', 'QingdaoTaxSpider', 'report_tax_qingdao'),
    'hubei': ('tax_hubei_spider.py', 'HubeiTaxSpider', 'report_tax_hubei'),
    'nmg': ('tax_nmg_spider.py', 'NmgTaxSpider', 'report_tax_nmg'),
    'shanxi': ('tax_shanxi_spider.py', 'ShanxiTaxSpider', 'report_tax_shanxi'),
    'xinjiang': ('tax_xinjiang_spider.py', 'XinjiangTaxSpider', 'report_tax_xinjiang'),
    'xizang': ('tax_xizang_spider.py', 'XizangTaxSpider', 'report_tax_xizang'),
    'yunnan': ('tax_yunnan_spider.py', 'YunnanTaxSpider', 'report_tax_yunnan'),
    'zhejiang': ('tax_zhejiang_spider.py', 'ZhejiangTaxSpider', 'report_tax_zhejiang'),
    'xiamen': ('tax_xiamen_spider.py', 'XiamenTaxSpider', 'report_tax_xiamen'),
    'ningbo': ('tax_ningbo_spider.py', 'NingboTaxSpider', 'report_tax_ningbo'),
    'shanghai': ('tax_shanghai_spider.py', 'ShanghaiTaxSpider', 'report_tax_shanghai'),
}

# Pagesize mode: 每页条数
PAGE_SIZES = {
    'hunan': 15, 'jilin': 20, 'shandong': 15, 'qingdao': 15,
    'hubei': 15, 'nmg': 15, 'shanxi': 15, 'xinjiang': 15,
    'xizang': 15, 'yunnan': 15, 'zhejiang': 15, 'xiamen': 15, 'ningbo': 15,
}

# URL templates per province
URLS = {
    'hunan': ("https://hunan.chinatax.gov.cn/lists/20190409002106/{page}", 'CUSTOM_PAGE'),
    'jilin': ("http://jilin.chinatax.gov.cn/col/col404/index.html?uid=16050&pageNum={page}", 'CUSTOM_PAGE'),
    'shandong': ("http://shandong.chinatax.gov.cn/module/web/jpage/dataproxy.jsp", 'POST_API'),
    'qingdao': ("http://qingdao.chinatax.gov.cn/module/web/jpage/dataproxy.jsp", 'POST_API'),
    'hubei': ("https://hubei.chinatax.gov.cn/hbsw/xxgk/tzgg/index{page}.html", 'GET_PAGE_FMT'),
    'nmg': ("http://neimenggu.chinatax.gov.cn/nmgsw/sscx2015/tzgg_{page}.html", 'GET_PAGE_FMT'),
    'shanxi': ("http://shanxi.chinatax.gov.cn/module/web/jpage/dataproxy.jsp", 'POST_API'),
    'xinjiang': ("https://xinjiang.chinatax.gov.cn/module/web/jpage/dataproxy.jsp", 'POST_API'),
    'xizang': ("https://xizang.chinatax.gov.cn/module/web/jpage/dataproxy.jsp", 'POST_API'),
    'yunnan': ("https://yunnan.chinatax.gov.cn/module/web/jpage/dataproxy.jsp", 'POST_API'),
    'zhejiang': ("https://zhejiang.chinatax.gov.cn/module/web/jpage/dataproxy.jsp", 'POST_API'),
    'xiamen': ("https://xiamen.chinatax.gov.cn/module/web/jpage/dataproxy.jsp", 'POST_API'),
    'ningbo': ("https://ningbo.chinatax.gov.cn/api-gateway/jpaas-publish-server/front/page/build/unit", 'POST_API'),
    'shanghai': ("https://shanghai.chinatax.gov.cn/module/web/jpage/dataproxy.jsp", 'POST_API'),
}

SOURCES = {
    'hunan': '国家税务总局湖南省税务局', 'jilin': '国家税务总局吉林省税务局',
    'shandong': '国家税务总局山东省税务局', 'qingdao': '国家税务总局青岛市税务局',
    'hubei': '国家税务总局湖北省税务局', 'nmg': '国家税务总局内蒙古自治区税务局',
    'shanxi': '国家税务总局山西省税务局', 'xinjiang': '国家税务总局新疆自治区税务局',
    'xizang': '国家税务总局西藏自治区税务局', 'yunnan': '国家税务总局云南省税务局',
    'zhejiang': '国家税务总局浙江省税务局', 'xiamen': '国家税务总局厦门市税务局',
    'ningbo': '国家税务总局宁波市税务局',
    'shanghai': '国家税务总局上海市税务局',
}

# XPaths for each province
XPATHS = {
    'hunan': {
        'list': "//div[@id='newsRight']/ul/li[(a)]",
        'title': "./a/@title", 'href': "./a/@href",
        'date': "./a/span[@class='rightdate']/text()",
        'detail': "//div[@class='dynamic-detail__content']",
        'attach': "//div[@class='dynamic-detail__content']//a[contains(@href,'.pdf') or contains(@href,'.doc')]",
    },
    'jilin': {
        'list': "//script[@type='text/xml']/text()",
        'title': ".//a/text()", 'href': ".//a/@href", 'date': ".//span/text()",
        'detail': "//div[@class='TRS_Editor']",
        'attach': "//div[@class='TRS_Editor']//a[contains(@href,'.pdf') or contains(@href,'.doc')]",
        'is_xml': True,  # special: XML recordset parsing
    },
    'shandong': {
        'list': "//script[@type='text/xml']/text()",
        'title': ".//a/text()", 'href': ".//a/@href", 'date': ".//span/text()",
        'detail': "//div[@class='TRS_Editor'] | //div[@id='fontzoom']",
        'attach': "//div[contains(@id,'zoom')]/p[(a) and contains(text(),'附件')]/a[(text())]",
        'is_xml': True,
    },
    'qingdao': {
        'list': "//ul/li",
        'title': "./a/text()", 'href': "./a/@href", 'date': "./span/text()",
        'detail': "//div[@id='zoom'] | //div[@class='TRS_Editor']",
        'attach': "//div[contains(@id,'zoom')]/p[(a) and contains(text(),'附件')]/a[(text())]",
    },
    'hubei': {
        'list': "//div[@class='lefbarbig']/ul/li",
        'title': "./a/text()", 'href': "./a/@href", 'date': "./span/text()",
        'detail': "//div[@class='TRS_Editor'] | //div[@id='fontzoom']",
        'attach': "//div[@id='download']/table//tr/td[a]",
    },
    'nmg': {
        'list': "//div[@class='list']/ul/li",
        'title': "./a/text()", 'href': "./a/@href", 'date': "./span/text()",
        'detail': "//div[@class='TRS_Editor'] | //div[@id='fontzoom']",
        'attach': "//div[contains(@id,'zoom')]/p[(a)]/a[(text())]",
    },
    'shanxi': {
        'list': "//script[@type='text/xml']/text()",
        'title': ".//a/text()", 'href': ".//a/@href", 'date': ".//span/text()",
        'detail': "//div[@class='TRS_Editor'] | //div[@id='fontzoom']",
        'attach': "//div[contains(@id,'zoom')]/p[(a) and contains(text(),'附件')]/a[(text())]",
        'is_xml': True,
    },
}

# Generate POST API template spiders
POST_TPL = '''"""{source}公告爬虫 → entity_government_announcement
旧项目参照: data_crawl_server {key}_tax_spider.py
"""
import hashlib, re, scrapy
from lxml import etree, html
from urllib.parse import urljoin
from spiders.base_spider import BaseSpider

_URL = '{url}'
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
            start = 1 if page == 1 else (page - 1) * 15 + 1
            end = 15 if start == 1 else start + 14
            yield scrapy.FormRequest(
                url=_URL, method='POST', headers=_H,
                formdata={{'startrecord': str(start), 'endrecord': str(end), 'perpage': '15'}},
                callback=self._parse_list, errback=self.errback,
            )

    def _parse_list(self, response):
        try:
            text = response.text
            rec = re.findall('<recordset>(.*?)</recordset>', text.replace('\\n', ''))
            if not rec:
                return
            lis = re.findall('<li.*?>(.*?)</li>', rec[0])
        except Exception:
            return
        for li_str in lis:
            try:
                row = etree.HTML(li_str)
            except Exception:
                continue
            title = ''.join(row.xpath('.//a/text()|.//a/@title')).strip()
            href = ''.join(row.xpath('.//a/@href')).strip()
            release_time = ''.join(row.xpath('.//span/text()')).strip()
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
                titles = [a.xpath('./text()')[0].strip() for a in atts if a.xpath('./text()')]
                hrefs = [a.xpath('./@href')[0].strip() for a in atts if a.xpath('./@href')]
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

# Generate GET HTML template spiders
GET_TPL = '''"""{source}公告爬虫 → entity_government_announcement
旧项目参照: data_crawl_server {key}_tax_spider.py
"""
import hashlib, scrapy
from lxml import etree, html
from urllib.parse import urljoin
from spiders.base_spider import BaseSpider

_URL_TPL = '{url}'
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

# Default XPath configs for provinces not explicitly configured
DEFAULT_XPATH = {
    'list': "//div[contains(@class,'list')]/ul/li",
    'title': "./a/text()", 'href': "./a/@href", 'date': "./span/text()",
    'detail': "//div[@id='zoom'] | //div[@id='img-content'] | //div[contains(@class,'ls-article-info')] | //div[@class='TRS_Editor'] | //div[@id='fontzoom']",
    'attach': "//div[contains(@id,'zoom')]/p[(a) and contains(text(),'附件')]/a[(text())]",
}

for key, (fname, class_name, spider_name) in sorted(REMAINING.items()):
    url, url_type = URLS[key]
    source = SOURCES[key]
    xp = XPATHS.get(key, DEFAULT_XPATH)

    if url_type == 'POST_API':
        code = POST_TPL.format(
            key=key, class_name=class_name, spider_name=spider_name,
            url=url, source=source,
            detail_xpath=xp['detail'], attach_xpath=xp['attach'],
        )
    else:
        code = GET_TPL.format(
            key=key, class_name=class_name, spider_name=spider_name,
            url=url, source=source,
            list_xpath=xp['list'], title_xpath=xp['title'],
            href_xpath=xp['href'], date_xpath=xp['date'],
            detail_xpath=xp['detail'], attach_xpath=xp['attach'],
        )

    with open(os.path.join(NEW, fname), 'w', encoding='utf-8') as f:
        f.write(code)
    print(f'  OK  {fname}  [{source}] ({url_type})')

print(f'\nGenerated: {len(REMAINING)}')
