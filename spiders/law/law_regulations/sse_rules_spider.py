# -*- coding: utf-8 -*-
"""
上交所官网「规则」栏目 采集爬虫 (单文件: 解析逻辑+爬虫)
========================================================
采集范围：https://www.sse.com.cn/lawandrules/ 下全部规则/法规/指南/征求意见/汇编，
并按栏目目录树输出 一级~六级 层级标签 + 法规状态。

自适应设计（网站变动不失效）：
  · 栏目树每次运行从全站菜单 /xhtml/js/sse_full.js 的 SSE_MENU_28 动态拉取，
    自动识别「规则」根栏目，无任何写死的栏目 id/名称/字典；
  · DISPLAY=0 的栏目(老版规则、已关闭栏目)自动整树跳过；
  · 总览/树状导览等无列表信息页自动抓取后判空跳过，不写死跳过清单；
  · 法规状态按栏目路径动态判定：已废止规则文本→已废止 / 业务规则废止公告→废止公告 / 其余→现行有效。

用法（本地冒烟测试，不写库）：
    scrapy crawl law_regulation_sse_rules -O sse_rules.json \
        -s ITEM_PIPELINES={} -s LOG_LEVEL=INFO
用法（正式入库，库表默认 sse_rule，可用 -a table=xxx 覆盖）：
    scrapy crawl law_regulation_sse_rules -a table=sse_rule
    scrapy crawl law_regulation_sse_rules -a reconcile=1   # 下线对账: 本批未采到的旧记录置 已下线
分页控制：-a start_page=1 -a end_page=2

入库字段：
    title / publish_time / rule_type / rule_status / url / source / channel_id /
    channel_name / tag_path / level_1..level_6 / md5_value
"""
import json
import re
import scrapy
from urllib.parse import urljoin

from spiders.base_spider import BaseSpider
from lxml import html as lh

SSE_HOME = 'https://www.sse.com.cn'
MENU_JS_URL = 'https://www.sse.com.cn/xhtml/js/sse_full.js'  # 全站菜单(含SSE_MENU_28)


# ---------------------------------------------------------------------------
# 一、菜单树（全动态，无写死栏目）
# ---------------------------------------------------------------------------
def extract_menu_obj(js_text: str) -> dict:
    """从 sse_full.js 提取 SSE_MENU_28（纯 JSON 字面量，括号配对后 json 解析）"""
    marker = 'SSE_MENU_28='
    i = js_text.find(marker)
    if i < 0:
        raise ValueError('sse_full.js 中未找到 SSE_MENU_28')
    depth = 0
    end = i
    for k in range(i, len(js_text)):
        if js_text[k] == '{':
            depth += 1
        elif js_text[k] == '}':
            depth -= 1
            if depth == 0:
                end = k
                break
    seg = js_text[i + len(marker):end + 1]
    return json.loads(seg)


def find_rules_root(tree: dict) -> str:
    """动态定位「规则」根栏目：CHNLNAME=规则 且 URL 位于 /lawandrules/ 下"""
    for k, v in tree.items():
        if v.get('CHNLNAME') == '规则' and (v.get('URL') or '').startswith('/lawandrules/'):
            return k
    raise ValueError('未能在菜单树中找到「规则」根栏目（网站栏目结构可能已调整）')


def walk_channels(tree: dict, root_id: str = None) -> list:
    """深度优先遍历「规则」子树，返回可见(菜单)频道列表

    · root_id 为空时自动识别根栏目
    · DISPLAY=0 的栏目（含子树）自动跳过
    返回元素: {channel_id, channel_name, url, path(祖先name列表,含自身), display, ntype}
    """
    if root_id is None:
        root_id = find_rules_root(tree)

    def _walk(node_id, path):
        node = tree.get(str(node_id))
        if not node:
            return
        name = node.get('CHNLNAME', '') or ''
        url = (node.get('URL', '') or '').strip()
        display = node.get('DISPLAY', '') or ''
        children = (node.get('CHILDREN', '') or '').strip()
        new_path = path + [name]
        # 非显示栏目整树跳过（老版规则/已关闭栏目）
        if display == '0':
            return
        if url.startswith('/lawandrules/'):
            yield {
                'channel_id': str(node_id),
                'channel_name': name,
                'url': url,
                'path': new_path,
                'display': display,
                'ntype': node.get('TYPE', '') or '',
            }
        if children:
            for c in children.split(';'):
                if c:
                    yield from _walk(c, new_path)

    yield from _walk(root_id, [])


def plan_crawl(channels: list) -> list:
    """决定实际要请求的列表页 URL 及其层级标签

    1. 同一 URL 被多个频道引用（父频道指向首个子频道页）时按 URL 分组取路径最深者；
    2. 聚合页（如 上市公司可转债 内联三个子列表）也保留，重复内容由 md5 去重兜底。
    """
    by_url = {}
    for ch in channels:
        by_url.setdefault(ch['url'], []).append(ch)

    result = []
    for url, group in by_url.items():
        rep = max(group, key=lambda ch: len(ch['path']))
        tags = {}
        for i, name in enumerate(rep['path']):
            if i < 6:
                tags[f'level_{i + 1}'] = name
        result.append({
            'url': url,
            'channel_id': rep['channel_id'],
            'channel_name': rep['channel_name'],
            'path': rep['path'],
            'tags': tags,
            'tag_path': '/'.join(rep['path']),
        })
    result.sort(key=lambda x: x['tag_path'])
    return result


# ---------------------------------------------------------------------------
# 二、列表解析（两种形态）
# ---------------------------------------------------------------------------
def parse_type_a(html_text: str) -> list:
    """解析 #sourceHtml 中的 @memo@/doc@ 碎片（本所业务规则分类页）"""
    m = re.search(r'<div id="sourceHtml"[^>]*>(.*?)</div>', html_text, re.S)
    if not m:
        return []
    content = re.sub(r'\s*@doc@\s*', '@doc@', m.group(1))
    content = re.sub(r'\s*@memo@\s*', '@memo@', content)
    items = []
    for seg in content.split('@doc@'):
        seg = seg.strip()
        if not seg:
            continue
        parts = seg.split('@memo@')
        if len(parts) < 4:
            continue
        rule_type, pub_date, link, title = (p.strip() for p in parts[:4])
        if not title or not link:
            continue
        items.append({'rule_type': rule_type, 'publish_time': pub_date,
                      'url': link.replace('/sse/', '/'), 'title': title})
    return items


_PAGER_RE = re.compile(
    r"createPageHTML\('(\w+)',\s*(\d+),\s*(\d+),\s*'(\w+)',\s*'(\w+)',\s*(\d+)\)")


def parse_type_b(html_text: str, page_url: str = ''):
    """解析 <dl><dd> 服务端渲染列表 + 分页信息

    返回: (items, pager_list)  pager_list: [{total_page, curr_page, next_url}]
    """
    root = lh.fromstring(html_text)
    items = []
    pager_list = []

    for block in root.xpath('//*[contains(@class, "js_listPage")]'):
        script = block.xpath('.//script[@id="pageParam"]')
        s_list_url = (script[0].get('url') or '').strip() if script else ''
        block_html = lh.tostring(block, encoding='unicode')
        for pm in _PAGER_RE.finditer(block_html):
            total_page, curr_page = int(pm.group(2)), int(pm.group(3))
            suffix = pm.group(5)
            next_url = ''
            if curr_page < total_page:
                base = s_list_url or (page_url.rstrip('/') + '/s_list.shtml')
                base = re.sub(r'\.shtml$', '', base)
                next_url = f'{base}_{curr_page + 1}.{suffix}'
            pager_list.append({'total_page': total_page, 'curr_page': curr_page,
                               'next_url': next_url})
        for dd in block.xpath('.//dl//dd'):
            a = dd.xpath('.//a')
            if not a:
                continue
            title = (a[0].get('title') or '').strip() or ''.join(a[0].xpath('.//text()')).strip()
            href = (a[0].get('href') or '').strip()
            sp = dd.xpath('.//span')
            date = ''.join(sp[0].xpath('.//text()')).strip() if sp else ''
            if title and href:
                items.append({'rule_type': '', 'publish_time': date, 'url': href, 'title': title})
    return items, pager_list


# ---------------------------------------------------------------------------
# 三、法规状态 + 组装
# ---------------------------------------------------------------------------
def rule_status_for(tag_path: str) -> str:
    """按栏目路径动态判定法规状态（网站自身语义）"""
    if '已废止规则文本' in tag_path:
        return '已废止'
    if '业务规则废止公告' in tag_path:
        return '废止公告'
    return '现行有效'


def build_item(parsed: dict, channel: dict, source: str = '上交所') -> dict:
    """组装最终入库字典（含层级标签 + 法规状态 + 去重 md5）"""
    from utils.tools import hash_md5
    url = urljoin(SSE_HOME, parsed['url'])
    title = parsed['title']
    md5_value = hash_md5(title + (parsed.get('publish_time') or '') + url)
    publish_time = (parsed.get('publish_time') or '').strip() or None  # 空日期入库为 NULL
    item = {
        'title': title,
        'publish_time': publish_time,
        'rule_type': parsed.get('rule_type') or '',
        'rule_status': rule_status_for(channel['tag_path']),
        'url': url,
        'source': source,
        'channel_id': channel['channel_id'],
        'channel_name': channel['channel_name'],
        'tag_path': channel['tag_path'],
        'md5_value': md5_value,
    }
    for k, v in channel['tags'].items():
        item[k] = v
    return item


# ---------------------------------------------------------------------------
# 四、爬虫
# ---------------------------------------------------------------------------
class SseRulesSpider(BaseSpider):
    name = 'law_regulation_sse_rules'
    data_table = 'sse_rule'          # 默认库表，可用 -a table=xxx 覆盖
    dedup_fields = ['md5_value']
    proxy_type = 'no_proxy'          # 国内站点，默认直连
    custom_settings = {
        'CONCURRENT_REQUESTS': 2,
        'DOWNLOAD_DELAY': 1,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 2,
    }
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://www.sse.com.cn/',
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                       '(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0'),
    }
    source_name = '上交所'

    def __init__(self, start_page=None, end_page=None, jobid=None, table=None,
                 max_channels=None, reconcile=None, **kwargs):
        super().__init__(start_page=start_page, end_page=end_page, jobid=jobid, **kwargs)
        if table:
            self.data_table = table
        self.max_channels = int(max_channels) if max_channels else 0
        self.reconcile = str(reconcile or '0') in ('1', 'true', 'yes')
        self._collected_md5s = set()
        self._request_errors = 0

    def start_requests(self):
        yield scrapy.Request(
            url=MENU_JS_URL, method='GET', headers=self.headers,
            callback=self.parse_menu, errback=self.errback,
        )

    def parse_menu(self, response):
        """解析全站菜单 -> 展开「规则」子树 -> 逐个请求列表页"""
        try:
            tree = extract_menu_obj(response.text)
            channels = list(walk_channels(tree))
            plan = plan_crawl(channels)
        except Exception as e:
            self.log_error(f'菜单解析失败: {e}')
            return
        if self.max_channels > 0:
            plan = plan[:self.max_channels]
        self.log_info(f'规则栏目频道 {len(channels)} 个, 列表页 {len(plan)} 个')
        for ch in plan:
            url = urljoin(SSE_HOME, ch['url'])
            self.log_info(f"采集列表页: {ch['tag_path']} -> {url}")
            yield scrapy.Request(
                url=url, method='GET', headers=self.headers,
                callback=self.parse_list, errback=self.errback,
                cb_kwargs={'channel': ch}, dont_filter=True,
            )

    def parse_list(self, response, channel):
        """解析列表页（兼容 @memo@ 碎片 与 <dl><dd> 两种形态），并跟进分页"""
        html_text = response.text

        # 形态 A: 本所业务规则分类页 (#sourceHtml @memo@/doc@ 碎片, 单页全量)
        items_a = parse_type_a(html_text)
        if items_a:
            self.log_info(f"{channel['tag_path']}: 规则 {len(items_a)} 条")
            for parsed in items_a:
                item = build_item(parsed, channel, source=self.source_name)
                self._collected_md5s.add(item['md5_value'])
                yield item
            return

        # 形态 B: 服务端 <dl><dd> 列表
        items_b, pagers = parse_type_b(html_text, response.url)
        if not items_b:
            self.log_warning(f"{channel['tag_path']}: 页面无列表数据 -> {response.url}")
            return
        self.log_info(f"{channel['tag_path']}: 规则 {len(items_b)} 条 (页 {response.url})")
        for parsed in items_b:
            if not parsed.get('rule_type'):
                parsed['rule_type'] = channel['channel_name']
            item = build_item(parsed, channel, source=self.source_name)
            self._collected_md5s.add(item['md5_value'])
            yield item

        # 分页跟进（受 start_page/end_page 约束）
        for pager in pagers:
            if not pager['next_url']:
                continue
            next_page_no = pager['curr_page'] + 1
            if next_page_no < self.start_page or next_page_no > self.end_page:
                continue
            yield scrapy.Request(
                url=urljoin(SSE_HOME, pager['next_url']), method='GET', headers=self.headers,
                callback=self.parse_list, errback=self.errback,
                cb_kwargs={'channel': channel}, dont_filter=True,
            )

    def errback(self, failure):
        self._request_errors += 1
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')

    def closed(self, reason):
        """下线对账: -a reconcile=1 时，将本批未采集到的旧记录状态置为 已下线
        （scrapy 结束时自动调用 spider.closed）"""
        if not self.reconcile:
            return
        if not self._collected_md5s:
            self.log_warning('本次未采集到任何记录，跳过对账（防止误判全量下线）')
            return
        if self._request_errors > 0:
            self.log_warning(f'本次存在 {self._request_errors} 个请求失败，跳过对账')
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
