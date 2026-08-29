"""为 POST API 税局蜘蛛的 start_requests 添加 _params 合并到 formdata"""
import os

TAX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'spiders', 'report', 'tax_bureau')

FILES = ['tax_gansu_spider.py','tax_hlj_spider.py','tax_jiangxi_spider.py',
         'tax_liaoning_spider.py','tax_ningxia_spider.py','tax_sichuan_spider.py']

for fname in FILES:
    fpath = os.path.join(TAX, fname)
    if not os.path.exists(fpath):
        continue
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace: formdata=self._post_data(),
    # With:    fd = self._post_data()\n            fd.update(self._params(page))\n            formdata=fd,
    old = '            formdata=self._post_data(),\n            callback=self._parse_list, errback=self.errback,'
    new = '            fd = self._post_data()\n            fd.update(self._params(page))\n            yield scrapy.FormRequest(\n                url=_URL, method=\'POST\', headers=_H,\n                formdata=fd,\n                callback=self._parse_list, errback=self.errback,'

    if old in content:
        # Also remove the yield scrapy.FormRequest line before it
        content = content.replace(
            '            yield scrapy.FormRequest(\n                url=_URL, method=\'POST\', headers=_H,\n' + old,
            new
        )
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'  OK {fname}')
    else:
        print(f'  SKIP {fname} (pattern not found)')

print('Done')
