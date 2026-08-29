# -*- coding: utf-8 -*-
"""
北交所官网「规则」栏目 采集爬虫 (单文件: 解析逻辑+爬虫)
========================================================
采集范围：https://www.bse.cn/ 下 法律规则(/rule/*) 与 业务规则(/business/*) 全部文档，
输出 一级~四级 层级标签；可选抓详情页补充法规状态（时效性/实施日期/发文字号等）。

自适应设计（网站变动不失效）：
  · 栏目清单每次运行从 https://www.bse.cn/rule/law_list.html 导航菜单动态解析，
    不写死栏目列表与节点 id；
  · 每个栏目页 #curNodeId 动态提取节点 id；监管规则适用指引页 #select_main 的
    子栏目动态解析后作为独立频道采集；
  · 层级名称按页面 URL 结构规则映射（页面文件名→中文名，网站自身分类），新增/改名
    栏目自动落入“菜单名”兜底，不中断采集；
  · 法规状态（时效性等）仅业务规则详情页有，-a fetch_detail=1 时抓取。

数据接口：POST https://www.bse.cn/info/listse.do （JSONP，nodeIds[]=栏目节点id）

用法（本地冒烟测试，不写库）：
    scrapy crawl law_regulation_bse_rules -O bse_rules.json \
        -s ITEM_PIPELINES={} -s LOG_LEVEL=INFO
用法（正式入库，库表默认 bse_rule）：
    scrapy crawl law_regulation_bse_rules -a table=bse_rule
    scrapy crawl law_regulation_bse_rules -a fetch_detail=1   # 业务规则补充法规状态
    scrapy crawl law_regulation_bse_rules -a reconcile=1      # 下线对账
分页控制：-a start_page=1 -a end_page=2
"""
import json
import re
import scrapy
from urllib.parse import urljoin

from spiders.base_spider import BaseSpider
from lxml import html as lh

BSE_HOME = 'https://www.bse.cn'
LAW_LIST_URL = 'https://www.bse.cn/rule/law_list.html'
API_URL = 'https://www.bse.cn/info/listse.do'
PAGE_SIZE = 20
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0')

# 页面路径(去 .html) -> (一级, 二级, 三级, 四级) 中文名（网站自身分类；未命中兜底）
_LEVEL_MAP = {
    'rule/law_list': ('规则', '法律规则', '法律', ''),
    'rule/council_list': ('规则', '法律规则', '行政法规', ''),
    'rule/justice_list': ('规则', '法律规则', '司法解释', ''),
    'rule/regulation_list': ('规则', '法律规则', '部门规章', ''),
    'rule/secnotice_list': ('规则', '法律规则', '证监会公告', ''),
    'rule/guide_list': ('规则', '法律规则', '监管规则适用指引', ''),
    'rule/Service_info': ('规则', '法律规则', '服务指南', ''),
    'rule/public_opinion': ('规则', '法律规则', '公开征求意见', ''),
    'business/fxrz_list': ('规则', '业务规则', '股票', '发行上市审核'),
    'business/cxjg_list': ('规则', '业务规则', '股票', '持续监管'),
    'business/jygl_list': ('规则', '业务规则', '股票', '交易管理'),
    'business/fxrzzq_list': ('规则', '业务规则', '债券', '发行上市审核'),
    'business/cxjgzq_list': ('规则', '业务规则', '债券', '持续监管'),
    'business/jyglzq_list': ('规则', '业务规则', '债券', '交易管理'),
    'business/scgl_list': ('规则', '业务规则', '市场管理', ''),
    'node/latestRule': ('规则', '业务规则', '最新规则', ''),
}


# ---------------------------------------------------------------------------
# 一、栏目清单（运行时从导航菜单解析）
# ---------------------------------------------------------------------------
def parse_nav_channels(page_html: str) -> list:
    """解析侧边导航菜单 -> [(菜单名, 页面路径)]，仅保留规则/业务/最新规则相关页面

    · 子菜单(subMenu)优先，顶层菜单(navMenu)兜底，按页面路径去重（同一页面只采一次）
    """
    root = lh.fromstring(page_html)
    seen = set()
    out = []
    for ul_cls in ('subMenu', 'navMenu'):
        for a in root.xpath(f'//ul[contains(@class, "{ul_cls}")]//a[@href]'):
            href = (a.get('href') or '').strip()
            if not re.match(r'^/(?:rule|business|node)/', href):
                continue
            name = (a.text_content() or '').strip()
            path = href.strip('/').replace('.html', '')
            if not name or path in seen:
                continue
            seen.add(path)
            out.append((name, path))
    return out


def build_channel(name: str, path: str, node_id: str = '') -> dict:
    """导航项 -> 采集频道（层级按页面路径规则映射，未命中用菜单名兜底）"""
    l1, l2, l3, l4 = _LEVEL_MAP.get(path, ('规则', '', name, ''))
    if not l2:
        l2 = '其他'
    if not l3:
        l3 = name
    parts = [p for p in (l1, l2, l3, l4) if p]
    tags = {'level_1': l1, 'level_2': l2}
    if l3:
        tags['level_3'] = l3
    if l4:
        tags['level_4'] = l4
    return {
        'name': name,
        'path': path,
        'url': f'{BSE_HOME}/{path}.html',
        'node_id': node_id,
        'tags': tags,
        'tag_path': '/'.join(parts),
        'has_detail_status': l2 == '业务规则',   # 仅业务规则详情页有 时效性 等标签
    }


def extract_node_id(html_text: str) -> str:
    """从栏目页 #curNodeId 提取节点id"""
    m = re.search(r'id="curNodeId"[^>]*value="(\d+)"', html_text)
    return m.group(1) if m else ''


def parse_select_main(html_text: str) -> list:
    """解析 #select_main 的 data 属性（JSON，容忍尾逗号） -> [{name, nodeid}]"""
    m = re.search(r'id="select_main"[^>]*data="([^"]*)"', html_text)
    if not m:
        return []
    raw = m.group(1).strip()
    if raw in ('', '[]', '[ ]'):
        return []
    cleaned = re.sub(r',\s*\]', ']', re.sub(r'\s+', '', raw))
    try:
        arr = json.loads(cleaned)
        return [{'name': x.get('name'), 'nodeid': str(x.get('nodeid'))}
                for x in arr if x.get('nodeid')]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# 二、列表接口
# ---------------------------------------------------------------------------
_JSONP_RE = re.compile(r'null\((.*)\)', re.S)


def parse_list_response(resp_text: str) -> dict:
    """解析 JSONP 列表响应 -> {'total': n, 'items': [...]}"""
    m = _JSONP_RE.search(resp_text)
    if not m:
        return {'total': 0, 'items': []}
    try:
        arr = json.loads(m.group(1))
    except Exception:
        return {'total': 0, 'items': []}
    if not arr or not arr[0].get('result'):
        return {'total': 0, 'items': []}
    data = arr[0].get('data') or {}
    return {'total': data.get('totalElements') or 0, 'items': data.get('content') or []}


def parse_api_item(item: dict, channel: dict) -> dict:
    """API 单条 -> 标准字段"""
    html_url = item.get('htmlUrl') or ''
    file_url = item.get('fileUrl') or ''
    if html_url.startswith('/'):
        html_url = urljoin(BSE_HOME, html_url)
    if file_url.startswith('/'):
        file_url = urljoin(BSE_HOME, file_url)
    publish_date = (item.get('publishDate') or '').strip()
    if len(publish_date) >= 10:
        publish_date = publish_date[:10]
    return {
        'info_id': str(item.get('infoId') or ''),
        'title': (item.get('title') or '').strip(),
        'publish_time': publish_date or None,
        'url': html_url or file_url,
        'has_html': bool(html_url),
        'file_url': file_url,
        'file_name': item.get('fileName') or '',
    }


def parse_detail_labels(html_text: str) -> dict:
    """解析详情页 nf_label/nf_text -> {时效性, 实施日期, 发文字号, 规则类别, 业务规则层级}"""
    try:
        root = lh.fromstring(html_text)
    except Exception:
        return {}
    out = {}
    for lab in root.xpath('//*[contains(@class, "nf_label")]'):
        name = (lab.text_content() or '').strip().replace('【', '').replace('】', '')
        parent = lab.getparent()
        texts = parent.xpath('.//*[contains(@class, "nf_text")]') if parent is not None else []
        value = (texts[0].text_content() or '').strip() if texts else ''
        if name:
            out[name] = value
    return out


# ---------------------------------------------------------------------------
# 三、组装（DATE 列空值转 None，避免 MySQL 严格模式报错）
# ---------------------------------------------------------------------------
def build_item(parsed: dict, channel: dict, detail: dict = None,
               source: str = '北交所') -> dict:
    """组装最终入库字典（含层级标签 + 法规状态 + 去重 md5）"""
    from utils.tools import hash_md5
    detail = detail or {}
    md5_value = hash_md5(parsed['title'] + (parsed['publish_time'] or '') + parsed['url'])
    publish_time = (parsed['publish_time'] or '').strip() or None
    implement_date = (detail.get('实施日期') or '').strip() or None
    item = {
        'title': parsed['title'],
        'publish_time': publish_time,
        'rule_status': detail.get('时效性') or '',
        'implement_date': implement_date,
        'issue_number': detail.get('发文字号') or '',
        'rule_category': detail.get('规则类别') or '',
        'rule_level': detail.get('业务规则层级') or '',
        'url': parsed['url'],
        'file_url': parsed['file_url'],
        'source': source,
        'channel_id': channel.get('node_id', ''),
        'channel_name': channel['name'],
        'tag_path': channel['tag_path'],
        'md5_value': md5_value,
    }
    for k, v in channel['tags'].items():
        item[k] = v
    return item


# ---------------------------------------------------------------------------
# 四、爬虫
# ---------------------------------------------------------------------------
class BseRulesSpider(BaseSpider):
    name = 'law_regulation_bse_rules'
    data_table = 'bse_rule'            # 默认库表，可用 -a table=xxx 覆盖
    dedup_fields = ['md5_value']
    proxy_type = 'no_proxy'            # 国内站点，默认直连
    custom_settings = {
        'CONCURRENT_REQUESTS': 2,
        'DOWNLOAD_DELAY': 1,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 2,
    }
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://www.bse.cn/',
        'User-Agent': UA,
    }
    source_name = '北交所'

    def __init__(self, start_page=None, end_page=None, jobid=None, table=None,
                 max_channels=None, fetch_detail=None, reconcile=None, **kwargs):
        super().__init__(start_page=start_page, end_page=end_page, jobid=jobid, **kwargs)
        if table:
            self.data_table = table
        self.max_channels = int(max_channels) if max_channels else 0
        self.fetch_detail = str(fetch_detail or '0') in ('1', 'true', 'yes')
        self.reconcile = str(reconcile or '0') in ('1', 'true', 'yes')
        self._collected_md5s = set()
        self._request_errors = 0

    def start_requests(self):
        yield scrapy.Request(
            url=LAW_LIST_URL, method='GET', headers=self.headers,
            callback=self.parse_nav, errback=self.errback,
        )

    def parse_nav(self, response):
        """导航菜单 -> 栏目清单 -> 逐栏目请求栏目页提取节点id"""
        try:
            nav = parse_nav_channels(response.text)
        except Exception as e:
            self.log_error(f'导航菜单解析失败: {e}')
            return
        channels = [build_channel(name, path) for name, path in nav]
        if self.max_channels > 0:
            channels = channels[:self.max_channels]
        self.log_info(f'北交所规则栏目 {len(channels)} 个 (导航动态解析)')
        for ch in channels:
            yield scrapy.Request(
                url=ch['url'], method='GET', headers=self.headers,
                callback=self.parse_channel_page, errback=self.errback,
                cb_kwargs={'channel': ch}, dont_filter=True,
            )

    def parse_channel_page(self, response, channel):
        """栏目页 -> 取节点id -> 请求列表接口；指南页附带解析子栏目"""
        node_id = extract_node_id(response.text)
        if not node_id:
            self.log_warning(f"{channel['name']}: 无节点id -> {response.url}")
            return
        channel['node_id'] = node_id
        self.log_info(f"{channel['name']}: node={node_id}")
        yield self._api_request(channel, 1)
        # 监管规则适用指引页: 子栏目(#select_main)动态展开为独立频道
        if channel['path'] == 'rule/guide_list':
            for sub in parse_select_main(response.text):
                sub_ch = build_channel(
                    f"监管规则适用指引-{sub['name']}", channel['path'], sub['nodeid'])
                sub_ch['tags']['level_4'] = sub['name']
                sub_ch['tag_path'] = channel['tag_path'] + '/' + sub['name']
                self.log_info(f"指南子栏目: {sub_ch['name']} node={sub['nodeid']}")
                yield self._api_request(sub_ch, 1)

    def _api_request(self, channel, page):
        return scrapy.FormRequest(
            url=API_URL + f'?t={abs(hash(channel["node_id"])) % 99999}',
            method='POST', headers=self.headers,
            formdata={
                'page': str(page), 'pageSize': str(PAGE_SIZE), 'keywords': '',
                'startTime': '', 'endTime': '', 'nodeIds[]': channel['node_id'],
                'needFields': '["infoId","title","linkUrl","htmlUrl","publishDate","fileUrl"]',
            },
            callback=self.parse_list, errback=self.errback,
            cb_kwargs={'channel': channel, 'page': page}, dont_filter=True,
        )

    def parse_list(self, response, channel, page):
        """列表接口 -> 逐条产出 + 翻页"""
        result = parse_list_response(response.text)
        total = result['total']
        items = result['items']
        self.log_info(f"{channel['name']}: 第{page}页 {len(items)} 条 (total={total})")
        for row in items:
            p = parse_api_item(row, channel)
            if not p['title']:
                continue
            if self.fetch_detail and channel['has_detail_status'] and p['has_html']:
                yield scrapy.Request(
                    url=p['url'], method='GET', headers=self.headers,
                    callback=self.parse_detail, errback=self.errback,
                    cb_kwargs={'parsed': p, 'channel': channel}, dont_filter=True,
                )
            else:
                item = build_item(p, channel)
                self._collected_md5s.add(item['md5_value'])
                yield item

        if page * PAGE_SIZE < total and page < self.end_page:
            yield self._api_request(channel, page + 1)

    def parse_detail(self, response, parsed, channel):
        detail = parse_detail_labels(response.text)
        item = build_item(parsed, channel, detail=detail)
        self._collected_md5s.add(item['md5_value'])
        yield item

    def errback(self, failure):
        self._request_errors += 1
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')

    def closed(self, reason):
        """下线对账: -a reconcile=1 时，将本批未采集到的旧记录状态置为 已下线
        （scrapy 结束时自动调用 spider.closed）"""
        if not self.reconcile:
            return
        if not self._collected_md5s or self._request_errors > 0:
            self.log_warning('本次无采集记录或存在请求失败，跳过对账')
            return
        try:
            import pymysql
            from pymysql.cursors import DictCursor
            from config import DB_CONF
            conn = pymysql.connect(cursorclass=DictCursor, **DB_CONF)
            with conn.cursor() as cur:
                cur.execute(
                    f'SELECT md5_value FROM `{self.data_table}` '
                    f"WHERE source=%s AND rule_status!='已下线'",
                    (self.source_name,))
                db_md5s = {r['md5_value'] for r in cur.fetchall()}
            stale = db_md5s - self._collected_md5s
            if stale:
                with conn.cursor() as cur:
                    cur.execute(
                        f"UPDATE `{self.data_table}` SET rule_status='已下线' "
                        f"WHERE source=%s AND md5_value IN ({','.join(['%s'] * len(stale))})",
                        (self.source_name, *stale))
                conn.commit()
                self.log_info(f'对账: 库内 {len(db_md5s)} 条, 本次采到 {len(self._collected_md5s)} 条, '
                              f'标记已下线 {len(stale)} 条')
            else:
                self.log_info(f'对账: 无下线记录 (库内 {len(db_md5s)} 条全部覆盖)')
            conn.close()
        except Exception as e:
            self.log_error(f'对账失败: {e}')
