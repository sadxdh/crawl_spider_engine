"""
法律法规爬虫（law_regulation）
数据来源：全国人大法律法规信息库 flk.npc.gov.cn

覆盖6类法律：
  宪法、法律、行政法规、监察法规、司法解释、地方性法规

增量策略：
  start_page=1 end_page=2（每类前2页，每页20条）
  去重字段：md5_value（title + timeliness 的 md5）

本地调试：
  scrapy crawl law_regulation -a start_page=1 -a end_page=2
"""
import hashlib
import json
from datetime import datetime
import scrapy

from spiders.base_spider import BaseSpider

_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/130.0.0.0 Safari/537.36'
)

# law_category → flfgCodeId 整数列表（来自 NPC API 实际参数）
_LAW_CATEGORIES = {
    '宪法':       [100],
    '法律':       [101, 102, 110, 120, 130, 140, 150, 160, 170, 180, 190, 195, 200],
    '行政法规':   [201, 210, 215],
    '监察法规':   [220],
    '司法解释':   [311, 320, 330, 340, 350],
    '地方性法规': [221, 222, 230, 260, 270, 290, 295, 300, 305, 310],
}

# sxx 整数 → 时效性文字
_TIMELINESS = {3: '有效', 4: '尚未生效', 2: '已修改', 1: '已废止'}

_LIST_URL = 'https://flk.npc.gov.cn/law-search/search/list'

def _md5(*parts) -> str:
    return hashlib.md5(''.join(str(p or '') for p in parts).encode()).hexdigest()

class LawRegulationSpider(BaseSpider):
    """全国人大法律法规爬虫"""

    name         = 'law_regulation'
    data_table   = 'law_regulation'
    dedup_fields = ['md5_value']

    allowed_domains = ['flk.npc.gov.cn']
    default_end_page = 2

    custom_settings = {
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
    }

    def start_requests(self):
        for law_category, code_ids in _LAW_CATEGORIES.items():
            for page in range(self.start_page, self.end_page + 1):
                yield scrapy.Request(
                    url=_LIST_URL,
                    method='POST',
                    body=json.dumps({
                        'searchRange': 1,
                        'sxrq': [],
                        'gbrq': [],
                        'searchType': 2,
                        'sxx': [],
                        'gbrqYear': [],
                        'flfgCodeId': code_ids,
                        'zdjgCodeId': [],
                        'searchContent': '',
                        'orderByParam': {'order': '-1', 'sort': ''},
                        'pageNum': page,
                        'pageSize': 20,
                    }),
                    headers={
                        'User-Agent': _UA,
                        'Content-Type': 'application/json;charset=UTF-8',
                        'Accept': 'application/json, text/plain, */*',
                        'Referer': 'https://flk.npc.gov.cn/search',
                        'Origin': 'https://flk.npc.gov.cn',
                    },
                    callback=self._parse_law_list,
                    errback=self.errback,
                    meta={'law_category': law_category},
                )

    def _parse_law_list(self, response):
        law_category = response.meta['law_category']
        try:
            data = response.json()
            rows = data.get('rows') or []
        except Exception:
            return

        for row in rows:
            title        = (row.get('title') or '').strip()
            sxx          = row.get('sxx')
            timeliness   = _TIMELINESS.get(sxx, 'xxx')
            publish_date = (row.get('gbrq') or '')[:10]
            entry_time   = (row.get('sxrq') or '')[:10]
            authority    = (row.get('zdjgName') or '').strip()
            law_nature   = (row.get('flxz') or '').strip()
            detail_id    = row.get('bbbs') or ''

            if not title:
                continue

            ann_url = (
                f'https://flk.npc.gov.cn/law-search/download/mobile'
                f'?format=docx&bbbs={detail_id}'
            ) if detail_id else 'https://flk.npc.gov.cn/search'

            item = {}
            item['spider_name']           = self.name
            item['title']                 = title
            item['formulating_authority'] = authority
            item['law_nature']            = law_nature or law_category
            item['law_category']          = law_category
            item['timeliness']            = timeliness
            item['publish_date']          = publish_date
            item['entry_into_force_time'] = entry_time
            item['announcement_title']    = title
            item['announcement_url']      = ann_url
            item['oss_url']               = None
            item['md5_value']             = _md5(title, timeliness)
            yield item

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
