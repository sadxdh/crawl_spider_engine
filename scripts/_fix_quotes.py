"""修复 tax_bureau 蜘蛛中的 XPath 引号冲突"""
import os, re

TAX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'spiders', 'report', 'tax_bureau')

ERROR_FILES = {
    'tax_gansu_spider.py',
    'tax_hlj_spider.py',
    'tax_hubei_spider.py',
    'tax_hunan_spider.py',
    'tax_jiangsu_spider.py',
    'tax_jiangxi_spider.py',
    'tax_jilin_spider.py',
    'tax_ningxia_spider.py',
    'tax_nmg_spider.py',
    'tax_shenzhen_spider.py',
    'tax_sichuan_spider.py',
    'tax_tianjin_spider.py',
}

fixed = 0
for fname in sorted(os.listdir(TAX_DIR)):
    if fname not in ERROR_FILES:
        continue
    fpath = os.path.join(TAX_DIR, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Fix: XPath strings with nested double quotes inside double-quoted python strings
    # Pattern: "//...[@id="zoom"]..."/p..." → use single quotes for Python string
    # Or: replace inner " with escaped \"

    # Fix _ATTACH_XPATH lines with @id="zoom" inside double-quoted strings
    content = re.sub(
        r'(_ATTACH_XPATH\s*=\s*)"(//div\[@id="zoom"[^\]]*\].*?)"',
        r"\1'\2'",
        content
    )

    # Fix _ATTACH_XPATH with nested double quotes
    content = re.sub(
        r'(_ATTACH_XPATH\s*=\s*)"([^"]*@id="[^"]*"[^"]*)"',
        lambda m: m.group(1) + "'" + m.group(2) + "'",
        content
    )

    # Fix list_xpath with nested single quotes: '//div[@class='xxx']/ul/li'
    # Change outer quotes to double
    content = re.sub(
        r"(_LIST_XPATH\s*=\s*|rows = tree\.xpath\()'([^']*@class='[^']*'[^']*)'",
        lambda m: m.group(1) + '"' + m.group(2) + '"',
        content
    )

    # Fix rows = tree.xpath('//...@id='main'...')
    content = re.sub(
        r"(rows = tree\.xpath\()'([^']*@id='[^']*'[^']*)'",
        lambda m: m.group(1) + '"' + m.group(2) + '"',
        content
    )

    # Fix _ATTACH_XPATH with @id='zoom' inside single-quoted strings containing double quotes
    # Actually, the simplest fix: for any remaining broken strings, manually check

    if content != original:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        fixed += 1
        print(f'  FIXED {fname}')
    else:
        print(f'  NO CHANGE {fname}')

print(f'\nFixed: {fixed}')
