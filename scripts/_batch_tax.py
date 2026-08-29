"""批量：用安徽模板 + 逐省配置替换，生成 POST dataproxy.jsp 省份蜘蛛"""
import os, re

OLD_DIR = r'C:\Users\24613\workstation\data_crawl_server\spider\report\gov_report\tax_bureau'
NEW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'spiders', 'report', 'tax_bureau')

# 省份 key → (新文件名, 类名, spider_name)
PROVINCES = {
    'dalian':   ('tax_dalian_spider',   'DalianTaxSpider',   'report_tax_dalian'),
    'gansu':    ('tax_gansu_spider',    'GansuTaxSpider',    'report_tax_gansu'),
    'hlj':      ('tax_hlj_spider',      'HljTaxSpider',      'report_tax_hlj'),
    'jiangsu':  ('tax_jiangsu_spider',  'JiangsuTaxSpider',  'report_tax_jiangsu'),
    'jiangxi':  ('tax_jiangxi_spider',  'JiangxiTaxSpider',  'report_tax_jiangxi'),
    'liaoning': ('tax_liaoning_spider', 'LiaoningTaxSpider', 'report_tax_liaoning'),
    'ningxia':  ('tax_ningxia_spider',  'NingxiaTaxSpider',  'report_tax_ningxia'),
    'sichuan':  ('tax_sichuan_spider',  'SichuanTaxSpider',  'report_tax_sichuan'),
}

# 安徽模板
with open(os.path.join(NEW_DIR, 'tax_anhui_spider.py'), 'r', encoding='utf-8') as f:
    TEMPLATE = f.read()


def read_func_body(content, func_name):
    """读取方法的完整 body（从 def 到下一个同缩进的 def）"""
    pattern = rf'    def {func_name}\((.*?)\n(.*?)(?=\n    def |\nclass |\Z)'
    m = re.search(pattern, content, re.DOTALL)
    return m.group(2) if m else ''


def extract_xpath_config(content):
    """提取 extract_detail 的 xpath_content 和 extract_attachment 的 xpath"""
    # detail xpath
    dm = re.search(r"xpath_content\s*=\s*'([^']+)'", content)
    if not dm:
        dm = re.search(r'xpath_content\s*=\s*"([^"]+)"', content)
    dx = dm.group(1) if dm else ''

    # attachment xpath
    am = re.search(r"\.xpath\('([^']+)'\)", content)
    ax = am.group(1) if am else ''

    return dx, ax


for key, (fname, class_name, spider_name) in sorted(PROVINCES.items()):
    old_path = os.path.join(OLD_DIR, f'{key}_tax_spider.py')
    new_path = os.path.join(NEW_DIR, f'{fname}.py')

    if not os.path.exists(old_path):
        print(f'  SKIP {key}: no old file')
        continue

    with open(old_path, 'r', encoding='utf-8') as f:
        old = f.read()

    # 提取配置
    url = re.search(r"self\.url\s*=\s*'([^']+)'", old).group(1)
    source = re.search(r'self\.website_source\s*=\s*"([^"]+)"', old)
    if not source:
        source = re.search(r"self\.website_source\s*=\s*'([^']+)'", old)
    source = source.group(1)

    # 提取 generate_params body
    params_body = read_func_body(old, 'generate_params')
    # 提取 generate_data body
    data_body = read_func_body(old, 'generate_data')
    # 提取 extract_detail + extract_attachment
    detail_body = read_func_body(old, 'extract_detail')
    dx, ax = extract_xpath_config(old)

    # 简化：普通参数的 generate_params 只有几行，直接用正则提取
    start_m = re.search(r'start\s*=\s*(.*?)\n', params_body)
    end_m = re.search(r'end\s*=\s*(.*?)\n', params_body)
    return_m = re.search(r'return\s*(\{.*?\})', params_body, re.DOTALL)
    params_return = return_m.group(1) if return_m else "{'startrecord': '', 'endrecord': '', 'perpage': '15'}"

    # 提取 generate_data 的 return dict
    data_return_m = re.search(r'return\s*(\{.*?\})', data_body, re.DOTALL)
    data_return = data_return_m.group(1) if data_return_m else '{}'

    # 生成蜘蛛代码
    spider = TEMPLATE
    spider = spider.replace("_URL = 'https://anhui.chinatax.gov.cn/module/web/jpage/dataproxy.jsp'",
                            f"_URL = '{url}'")
    spider = spider.replace("_SOURCE = '国家税务总局安徽省税务局'",
                            f"_SOURCE = '{source}'")
    spider = spider.replace("class AnhuiTaxSpider(BaseSpider):",
                            f"class {class_name}(BaseSpider):")
    spider = spider.replace("name = 'report_tax_anhui'",
                            f"name = '{spider_name}'")

    # 替换 _DETAIL_XPATH
    if dx:
        spider = re.sub(r"_DETAIL_XPATH = \(\s*\"[^\"]+\"(?:\s*\"[^\"]+\")*\s*\)",
                        f'_DETAIL_XPATH = "{dx}"', spider, flags=re.DOTALL)

    # 替换 _ATTACH_XPATH
    if ax:
        spider = re.sub(r'_ATTACH_XPATH = \(\s*"[^"]+"(?:\s*"[^"]+")*\s*\)',
                        f'_ATTACH_XPATH = "{ax}"', spider, flags=re.DOTALL)

    # 替换 _post_data
    if data_return != '{}':
        old_data = re.search(r'def _post_data\(\):\s*\n\s*return \{.*?\n    \}', spider, re.DOTALL)
        if old_data:
            new_data = f'def _post_data():\n        return {data_return}'
            spider = spider.replace(old_data.group(0), new_data)

    # 替换 _params
    if params_return:
        old_params = re.search(r'def _params\(page\):\s*\n\s*start.*?\n\s*return \{.*?\n    \}', spider, re.DOTALL)
        if old_params:
            new_params = f'def _params(page):\n        start = 1 if page == 1 else (page - 1) * 45 + 1\n        end = 45 if start == 1 else start + 44\n        return {params_return}'
            spider = spider.replace(old_params.group(0), new_params)

    with open(new_path, 'w', encoding='utf-8') as f:
        f.write(spider)

    print(f'  OK  {key} → {fname}.py  [{source}]')

print('\nDone!')
