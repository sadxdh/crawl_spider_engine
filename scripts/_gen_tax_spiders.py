"""从旧项目 tax_bureau 蜘蛛提取配置，生成新 Scrapy 蜘蛛。"""
import os, re, ast

OLD_DIR = r'C:\Users\24613\workstation\data_crawl_server\spider\report\gov_report\tax_bureau'
NEW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'spiders', 'report', 'tax_bureau')

# 已处理的旧→新省份名映射（旧文件名 → 新 class 名）
NAME_MAP = {
    'anhui': ('tax_anhui_spider', 'AnhuiTaxSpider', 'report_tax_anhui'),
    'beijing': ('tax_beijing_spider', 'BeijingTaxSpider', 'report_tax_beijing'),
    'chongqing': ('tax_chongqing_spider', 'ChongqingTaxSpider', 'report_tax_chongqing'),
    'dalian': ('tax_dalian_spider', 'DalianTaxSpider', 'report_tax_dalian'),
    'fujian': ('tax_fujian_spider', 'FujianTaxSpider', 'report_tax_fujian'),
    'gansu': ('tax_gansu_spider', 'GansuTaxSpider', 'report_tax_gansu'),
    'guangdong': ('tax_guangdong_spider', 'GuangdongTaxSpider', 'report_tax_guangdong'),
    'guangxi': ('tax_guangxi_spider', 'GuangxiTaxSpider', 'report_tax_guangxi'),
    'guizhou': ('tax_guizhou_spider', 'GuizhouTaxSpider', 'report_tax_guizhou'),
    'hainan': ('tax_hainan_spider', 'HainanTaxSpider', 'report_tax_hainan'),
    'hebei': ('tax_hebei_spider', 'HebeiTaxSpider', 'report_tax_hebei'),
    'henan': ('tax_henan_spider', 'HenanTaxSpider', 'report_tax_henan'),
    'hlj': ('tax_hlj_spider', 'HljTaxSpider', 'report_tax_hlj'),
    'hubei': ('tax_hubei_spider', 'HubeiTaxSpider', 'report_tax_hubei'),
    'hunan': ('tax_hunan_spider', 'HunanTaxSpider', 'report_tax_hunan'),
    'jiangsu': ('tax_jiangsu_spider', 'JiangsuTaxSpider', 'report_tax_jiangsu'),
    'jiangxi': ('tax_jiangxi_spider', 'JiangxiTaxSpider', 'report_tax_jiangxi'),
    'jilin': ('tax_jilin_spider', 'JilinTaxSpider', 'report_tax_jilin'),
    'liaoning': ('tax_liaoning_spider', 'LiaoningTaxSpider', 'report_tax_liaoning'),
    'ningxia': ('tax_ningxia_spider', 'NingxiaTaxSpider', 'report_tax_ningxia'),
    'nmg': ('tax_nmg_spider', 'NmgTaxSpider', 'report_tax_nmg'),
    'qinghai': ('tax_qinghai_spider', 'QinghaiTaxSpider', 'report_tax_qinghai'),
    'shandong': ('tax_shandong_spider', 'ShandongTaxSpider', 'report_tax_shandong'),
    'shanghai': ('tax_shanghai_spider', 'ShanghaiTaxSpider', 'report_tax_shanghai'),
    'shanxi': ('tax_shanxi_spider', 'ShanxiTaxSpider', 'report_tax_shanxi'),
    'shenzhen': ('tax_shenzhen_spider', 'ShenzhenTaxSpider', 'report_tax_shenzhen'),
    'sichuan': ('tax_sichuan_spider', 'SichuanTaxSpider', 'report_tax_sichuan'),
    'tianjin': ('tax_tianjin_spider', 'TianjinTaxSpider', 'report_tax_tianjin'),
    'xiamen': ('tax_xiamen_spider', 'XiamenTaxSpider', 'report_tax_xiamen'),
    'xinjiang': ('tax_xinjiang_spider', 'XinjiangTaxSpider', 'report_tax_xinjiang'),
    'xizang': ('tax_xizang_spider', 'XizangTaxSpider', 'report_tax_xizang'),
    'yunnan': ('tax_yunnan_spider', 'YunnanTaxSpider', 'report_tax_yunnan'),
    'zhejiang': ('tax_zhejiang_spider', 'ZhejiangTaxSpider', 'report_tax_zhejiang'),
}


def extract_str(content, var):
    """提取 self.var = 'value'"""
    m = re.search(rf"self\.{var}\s*=\s*'([^']*)'", content)
    if not m:
        m = re.search(rf'self\.{var}\s*=\s*"([^"]*)"', content)
    return m.group(1) if m else ''


def extract_xpath(content, func_name):
    """提取 xpath_content = '...'"""
    m = re.search(rf"def {func_name}\(self.*?\n(.*?)(?=\n    def |\n$)", content, re.DOTALL)
    if not m:
        return '', ''
    body = m.group(1)
    xpath_m = re.search(r"xpath_content\s*=\s*'([^']*)'", body)
    if not xpath_m:
        xpath_m = re.search(r'xpath_content\s*=\s*"([^"]*)"', body)
    detail_xpath = xpath_m.group(1) if xpath_m else ''

    # extract_attachment xpath
    att_m = re.search(r"def extract_attachment\(self.*?\n(.*?)(?=\n    def |\n$)", body, re.DOTALL) if func_name == 'extract_detail' else None
    if not att_m:
        att_m = re.search(rf"def extract_attachment\(self.*?\n(.*?)(?=\n    def |\n$)", content, re.DOTALL)
    att_xpath = ''
    if att_m:
        ax = re.search(r"\.xpath\('([^']*)'\)", att_m.group(1))
        att_xpath = ax.group(1) if ax else ''

    return detail_xpath, att_xpath


def generate_spider(key, info):
    """根据配置生成完整的 Scrapy 蜘蛛文件"""
    fname, class_name, spider_name = NAME_MAP[key]
    url = info.get('url', '')
    source = info.get('source', '')
    params_func = info.get('params', '')
    data_func = info.get('data', '')
    detail_xpath = info.get('detail_xpath', '')
    att_xpath = info.get('att_xpath', '')

    # 默认 XPath（如果旧项目没定义）
    if not detail_xpath:
        detail_xpath = "//div[@id='zoom'] | //div[@id='img-content'] | //div[contains(@class,'ls-article-info')] | //div[@class='TRS_Editor'] | //div[@id='fontzoom']"
    if not att_xpath:
        att_xpath = "//div[contains(@id,'zoom')]/p[(a) and contains(text(),'附件')]/a[(text())]"

    params_lines = params_func.strip().split('\n') if params_func else []
    data_lines = data_func.strip().split('\n') if data_func else []

    content = f'''"""{source}公告爬虫 → entity_government_announcement
旧项目参照: data_crawl_server {fname}.py
"""
import hashlib, re, scrapy
from lxml import etree, html
from urllib.parse import urljoin
from spiders.base_spider import BaseSpider

_DETAIL_XPATH = "{detail_xpath}"
_ATTACH_XPATH = "{att_xpath}"
_SOURCE = "{source}"

_H = {{
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Content-Type': 'application/x-www-form-urlencoded',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
}}


class {class_name}(BaseSpider):
    name = '{spider_name}'
    data_table = 'entity_government_announcement'
    dedup_fields = ['md5_value']
    custom_settings = {{'CONCURRENT_REQUESTS': 3, 'DOWNLOAD_DELAY': 1}}

    _list_url = '{url}'

    @staticmethod
    def _post_data(page):
        return {data_func.strip()}

    @staticmethod
    def _params(page):
        return {params_func.strip()}

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            yield scrapy.FormRequest(
                url=self._list_url, method='POST',
                headers=_H,
                formdata=self._post_data(page),
                callback=self._parse_list, errback=self.errback,
                meta={{'page': page}},
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
            md5_value = hashlib.md5((str(release_time) + title + _SOURCE).encode()).hexdigest()
            yield scrapy.Request(
                url=url, callback=self._parse_detail, errback=self.errback,
                headers=_H,
                meta={{'title': title, 'release_time': release_time, 'url': url, 'md5_value': md5_value}},
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
                titles = []
                hrefs = []
                for a in atts:
                    t = a.xpath('./text()')
                    h = a.xpath('./@href')
                    if t and h:
                        titles.append(t[0].strip())
                        hrefs.append(response.urljoin(h[0].strip()))
                attachment_title = ','.join(titles) if titles else ''
                attachment_url = ','.join(hrefs) if hrefs else ''
            except Exception:
                pass

        yield {{
            'publish_time': meta['release_time'],
            'announcement_title': meta['title'],
            'announcement_url': meta['url'],
            'source': _SOURCE,
            'announcement_type': '',
            'abstract': '',
            'content': content,
            'emotion': '',
            'md5_value': meta['md5_value'],
            '_table': 'entity_government_announcement',
        }}

    def errback(self, failure):
        self.log_error(f'请求失败: {{failure.request.url}} — {{failure.value}}')
'''

    # 如果旧项目有特殊 generate_params（非默认），嵌入到 _params
    if params_func:
        # 提取所有参数行
        pass

    return content


# 主流程：处理所有 POST API 模式的省份
processed = 0
for key in sorted(NAME_MAP.keys()):
    fname, class_name, spider_name = NAME_MAP[key]
    old_path = os.path.join(OLD_DIR, f'{key}_tax_spider.py')
    new_fname = f'{fname}.py'
    new_path = os.path.join(NEW_DIR, new_fname)

    if not os.path.exists(old_path):
        print(f'  SKIP {key}: old file not found')
        continue

    with open(old_path, 'r', encoding='utf-8') as f:
        old_content = f.read()

    # 只有 POST jpage/dataproxy.jsp API 模式的处理
    url = extract_str(old_content, 'url')
    if 'dataproxy.jsp' not in url and 'was5/web/search' not in url and 'common/search' not in url:
        # 非 POST API 模式（如 GET HTML 页面），先跳过
        # 检查是否有 generate_params 方法 → POST 模式
        if 'def generate_params' not in old_content and 'def generate_data' not in old_content:
            print(f'  SKIP {key}: non-API pattern, needs manual rewrite')
            continue

    source = extract_str(old_content, 'website_source')
    detail_xpath, att_xpath = extract_xpath(old_content, 'extract_detail')

    # 提取 generate_params 方法体
    params_m = re.search(r'def generate_params\(self.*?\n(.*?)(?=\n    def |\n$)', old_content, re.DOTALL)
    params_body = params_m.group(1).strip() if params_m else ''

    # 提取 generate_data 方法体
    data_m = re.search(r'def generate_data\(self.*?\n(.*?)(?=\n    def |\n$)', old_content, re.DOTALL)
    data_body = data_m.group(1).strip() if data_m else ''

    # 生成蜘蛛
    info = {
        'url': url,
        'source': source,
        'params': params_body,
        'data': data_body,
        'detail_xpath': detail_xpath,
        'att_xpath': att_xpath,
    }

    spider_code = generate_spider(key, info)
    with open(new_path, 'w', encoding='utf-8') as f:
        f.write(spider_code)
    processed += 1
    print(f'  OK  {key} → {new_fname}')

print(f'\nProcessed: {processed}')
