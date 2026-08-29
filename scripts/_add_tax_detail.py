"""为 tax_bureau 蜘蛛添加详情页爬取。简化版：直接字符串替换。"""
import os, re

TAX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'spiders', 'report', 'tax_bureau')

patched = 0
for fname in sorted(os.listdir(TAX_DIR)):
    if not fname.endswith('.py') or fname.startswith('__'):
        continue
    fpath = os.path.join(TAX_DIR, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'def parse_detail' in content:
        print(f'  SKIP {fname} (already has detail)')
        continue

    # 提取 source 名称
    sm = re.search(r"'source':\s*'([^']+)'", content)
    if not sm:
        print(f'  SKIP {fname} (no source)')
        continue
    source = sm.group(1)

    # 提取 md5 表达式
    mm = re.search(r"'md5_value':\s*(hashlib\.md5\([^)]+\)\.hexdigest\(\))", content)
    md5_expr = mm.group(1) if mm else "''"

    # 替换 yield{...} 为 yield Request(...)
    # 匹配整个 yield dict 块
    old_yield = re.search(
        r"(\s*)(yield\{'publish_time':date,'announcement_title':title,\s*\n"
        r"\s*'announcement_url':url,'source':[^,]+,\s*\n"
        r"\s*'announcement_type':'',\s*\n"
        r"\s*'abstract':'',\s*\n"
        r"\s*'content':'',\s*\n"
        r"\s*'emotion':'',\s*\n"
        r"\s*'md5_value':[^,]+,\s*\n"
        r"\s*'_table':'entity_government_announcement'\})",
        content
    )
    if not old_yield:
        # Try alternate format (compact)
        old_yield = re.search(
            r"(\s*)(yield\{'publish_time':date,'announcement_title':title,\s*\n"
            r"\s*'announcement_url':url,'source':[^,]+,\s*\n"
            r"\s*'announcement_type':'',\s*\n"
            r"\s*'abstract':'',\s*\n"
            r"\s*'content':'',\s*\n"
            r"\s*'emotion':'',\s*\n"
            r"\s*'md5_value':\s*[^,]+,\s*\n"
            r"\s*'_table':'entity_government_announcement'\s*\})",
            content
        )
    if not old_yield:
        print(f'  SKIP {fname} (no yield match)')
        continue

    indent = old_yield.group(1)

    new_block = f"""{indent}md5_value = {md5_expr}
{indent}yield scrapy.Request(
{indent}    url=url, callback=self.parse_detail, errback=self.errback,
{indent}    headers=_H,
{indent}    meta={{'title': title, 'date': date, 'url': url,
{indent}           'source': '{source}', 'md5_value': md5_value}})
"""

    new_content = content.replace(old_yield.group(0), new_block)

    # 去掉旧的 errback 定义
    new_content = re.sub(
        r'\n(\s*)def errback\(self,\s*failure\):\s*[^\n]*\n(\s*)self\.log_error\(f.*\n',
        '', new_content
    )

    # 追加 parse_detail + errback
    append = f'''
    def parse_detail(self, response):
        meta = response.meta
        try:
            tree = etree.HTML(response.body)
        except Exception:
            tree = None
        content = ''
        if tree is not None:
            try:
                cn = tree.xpath("//div[@id='zoom'] | //div[@id='img-content'] | //div[contains(@class,'ls-article-info')] | //div[@class='TRS_Editor'] | //div[@id='fontzoom'] | //div[contains(@class,'news-content')]")
                if cn:
                    for bad in cn[0].xpath('.//script|.//style'):
                        p = bad.getparent()
                        if p is not None:
                            p.remove(bad)
                    content = etree.tostring(cn[0], encoding='unicode')
            except Exception:
                pass
        yield {{
            'publish_time': meta['date'],
            'announcement_title': meta['title'],
            'announcement_url': meta['url'],
            'source': meta['source'],
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

    new_content = new_content.rstrip() + append

    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    patched += 1
    print(f'  OK  {fname}')

print(f'\nPatched: {patched} spiders')
