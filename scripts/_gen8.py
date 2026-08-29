"""生成8个 POST dataproxy.jsp 省份蜘蛛"""
import os

NEW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'spiders', 'report', 'tax_bureau')

CONFIGS = [
    # (key, filename, class, spider_name, url, source, col, webid, path, columnid, unitid, webname, page_size, detail_xpath, attach_xpath)
    ('dalian', 'tax_dalian_spider.py', 'DalianTaxSpider', 'report_tax_dalian',
     'https://dalian.chinatax.gov.cn/module/web/jpage/dataproxy.jsp', '国家税务总局大连市税务局',
     '1', '2', 'http://dalian.chinatax.gov.cn/', '1715', '16477', '国家税务总局大连市税务局', 45,
     '', './/a/text()'),

    ('gansu', 'tax_gansu_spider.py', 'GansuTaxSpider', 'report_tax_gansu',
     'http://gansu.chinatax.gov.cn/module/web/jpage/dataproxy.jsp', '国家税务总局甘肃省税务局',
     '1', '1', 'http://gansu.chinatax.gov.cn/', '34', '35565', '国家税务总局甘肃省税务局', 30,
     '', '//div[@id="zoom"]/p[(a)]/a[(text())]'),

    ('hlj', 'tax_hlj_spider.py', 'HljTaxSpider', 'report_tax_hlj',
     'http://heilongjiang.chinatax.gov.cn/module/web/jpage/dataproxy.jsp', '国家税务总局黑龙江省税务局',
     '1', '18', 'http://heilongjiang.chinatax.gov.cn/', '16776', '43018', '国家税务总局黑龙江省税务局', 15,
     '', '//div[@id="zoom"]/p[(a)]/a[(text())]'),

    ('jiangsu', 'tax_jiangsu_spider.py', 'JiangsuTaxSpider', 'report_tax_jiangsu',
     'https://jiangsu.chinatax.gov.cn/module/web/jpage/dataproxy.jsp', '国家税务总局江苏省税务局',
     '1', '24', 'http://jiangsu.chinatax.gov.cn/', '19752', '47868', '国家税务总局江苏省税务局', 45,
     '', '//div[@id="zoom"]/p[(a) and contains(text(), "附件")]/a[(text())]'),

    ('jiangxi', 'tax_jiangxi_spider.py', 'JiangxiTaxSpider', 'report_tax_jiangxi',
     'https://jiangxi.chinatax.gov.cn/module/web/jpage/dataproxy.jsp', '国家税务总局江西省税务局',
     '1', '26', 'http://jiangxi.chinatax.gov.cn/', '31020', '56298', '国家税务总局江西省税务局', 45,
     '', '//div[@class="info-cont"]/p//a'),

    ('liaoning', 'tax_liaoning_spider.py', 'LiaoningTaxSpider', 'report_tax_liaoning',
     'https://liaoning.chinatax.gov.cn/module/web/jpage/dataproxy.jsp', '国家税务总局辽宁省税务局',
     '1', '54', 'http://liaoning.chinatax.gov.cn/', '1880', '10117', '国家税务总局辽宁省税务局', 45,
     '', './/a/text()'),

    ('ningxia', 'tax_ningxia_spider.py', 'NingxiaTaxSpider', 'report_tax_ningxia',
     'http://ningxia.chinatax.gov.cn/module/web/jpage/dataproxy.jsp', '国家税务总局宁夏自治区税务局',
     '1', '1', 'http://ningxia.chinatax.gov.cn/', '3016', '19732', '国家税务总局宁夏自治区税务局', 15,
     '', '//div[@id="zoom"]/p[(a)]/a[(text())]'),

    ('sichuan', 'tax_sichuan_spider.py', 'SichuanTaxSpider', 'report_tax_sichuan',
     'https://sichuan.chinatax.gov.cn/module/web/jpage/dataproxy.jsp', '国家税务总局四川省税务局',
     '1', '44', 'http://sichuan.chinatax.gov.cn/', '15391', '38718', '国家税务总局四川省税务局', 45,
     '', '//div[@id="zoom"]/p[(a) and contains(text(), "附件")]/a[(text())]'),
]

TPL = '''"""{source}公告爬虫 → entity_government_announcement
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

    @staticmethod
    def _post_data():
        return {{
            'col': '{col}', 'webid': '{webid}', 'path': '{path}',
            'columnid': '{columnid}', 'sourceContentType': '1', 'unitid': '{unitid}',
            'webname': '{webname}', 'permissiontype': '0',
        }}

    @staticmethod
    def _params(page):
        page_size = {page_size}
        start = 1 if page == 1 else (page - 1) * page_size + 1
        end = page_size if start == 1 else start + page_size - 1
        return {{'startrecord': str(start), 'endrecord': str(end), 'perpage': '15'}}

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            yield scrapy.FormRequest(
                url=_URL, method='POST', headers=_H,
                formdata=self._post_data(),
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
            title = ''.join(row.xpath('.//a/@title')).strip()
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
        detail_xpath = _DETAIL_XPATH or "//div[@id='zoom'] | //div[@id='img-content'] | //div[contains(@class,'ls-article-info')] | //div[@class='TRS_Editor'] | //div[@id='fontzoom']"
        if tree is not None:
            try:
                cn = tree.xpath(detail_xpath)
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

for cfg in CONFIGS:
    (key, fname, class_name, spider_name, url, source,
     col, webid, path, columnid, unitid, webname, page_size,
     detail_xpath, attach_xpath) = cfg

    # 默认 XPath
    dx = detail_xpath or (
        "//div[@id='zoom'] | //div[@id='img-content'] | "
        "//div[contains(@class,'ls-article-info')] | //div[@class='TRS_Editor'] | "
        "//div[@id='fontzoom']"
    )
    ax = attach_xpath or (
        "//div[contains(@id,'zoom')]/p[(a) and contains(text(),'附件')]/a[(text())]"
    )

    code = TPL.format(
        key=key, fname=fname, class_name=class_name, spider_name=spider_name,
        url=url, source=source, col=col, webid=webid, path=path,
        columnid=columnid, unitid=unitid, webname=webname, page_size=page_size,
        detail_xpath=dx, attach_xpath=ax,
    )

    fpath = os.path.join(NEW, fname)
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(code)
    print(f'  OK  {fname}  [{source}]')

print(f'\nGenerated: {len(CONFIGS)}')
