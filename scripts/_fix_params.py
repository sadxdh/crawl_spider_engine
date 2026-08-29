"""修复 POST API 税局蜘蛛: 把 _params 合并到 formdata"""
import os, re

TAX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'spiders', 'report', 'tax_bureau')

AFFECTED = ['tax_hlj_spider.py', 'tax_jiangxi_spider.py', 'tax_liaoning_spider.py',
            'tax_ningxia_spider.py', 'tax_shandong_spider.py', 'tax_shanxi_spider.py',
            'tax_xiamen_spider.py', 'tax_xinjiang_spider.py', 'tax_xizang_spider.py',
            'tax_yunnan_spider.py', 'tax_zhejiang_spider.py', 'tax_ningbo_spider.py',
            'tax_qingdao_spider.py', 'tax_sichuan_spider.py', 'tax_hubei_spider.py']

for fname in AFFECTED:
    fpath = os.path.join(TAX_DIR, fname)
    if not os.path.exists(fpath):
        continue
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix: replace broken pattern
    # From: yield scrapy.FormRequest( ... fd = self._post_data(); fd.update(...) ...
    # To:   fd = self._post_data(); fd.update(self._params(page))
    #       yield scrapy.FormRequest( ... formdata=fd, ... )

    # Pattern 1: broken inline statement
    broken = re.compile(
        r'(yield scrapy\.FormRequest\(\s*\n\s*url=_URL, method=.POST., headers=_H,\s*\n\s*)'
        r'fd = self\._post_data\(\); fd\.update\(self\._params\(page\)\)\s*\n\s*'
        r'(formdata=fd, callback=self\._parse_list)'
    )
    replacement = (
        r'fd = self._post_data()\n            fd.update(self._params(page))\n            '
        r'\1formdata=fd, callback=self._parse_list'
    )
    new_content = broken.sub(replacement, content)

    if new_content != content:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'  FIXED {fname}')
    else:
        print(f'  SKIP {fname} (no match)')
