# -*- coding: utf-8 -*-
"""
深交所官网「法律规则」栏目 采集爬虫 (单文件: 解析逻辑+爬虫)
============================================================
采集范围：https://www.szse.cn/lawrules/ 下 法律法规/部门规章/本所业务规则/
业务指南与流程/公开征求意见 全部文档，输出 一级~四级 层级标签 + 法规状态。

自适应设计（网站变动不失效）：
  · 栏目清单每次运行从 https://www.szse.cn/lawrules/index.html 侧边菜单动态解析，
    不写死栏目列表；
  · 每个栏目页内联脚本 cmsParam.currentMenuId 动态提取，作为 /api/search/content 的
    channelCode；
  · 层级名称按 URL 结构规则映射（URL 段→中文名，网站自身分类），新增/改名栏目自动
    落入“URL 段名/菜单名”兜底，不中断采集；
  · 法规状态按栏目路径动态判定：已废止规则文本→已废止 / 规则废止公告→废止公告 /
    指南与征求意见→空 / 其余→现行有效。

数据接口：POST https://www.szse.cn/api/search/content （表单 channelCode=currentMenuId）

用法（本地冒烟测试，不写库）：
    scrapy crawl law_regulation_szse_rules -O szse_rules.json \
        -s ITEM_PIPELINES={} -s LOG_LEVEL=INFO
用法（正式入库，库表默认 szse_rule）：
    scrapy crawl law_regulation_szse_rules -a table=szse_rule
    scrapy crawl law_regulation_szse_rules -a fetch_detail=1   # 已废止规则抓详情页补失效依据
    scrapy crawl law_regulation_szse_rules -a reconcile=1      # 下线对账
分页控制：-a start_page=1 -a end_page=2
"""
import re
import scrapy
from urllib.parse import urljoin

from spiders.base_spider import BaseSpider
from lxml import html as lh

SZSE_HOME = 'https://www.szse.cn'
LAWRULES_INDEX = 'https://www.szse.cn/lawrules/index.html'
API_URL = 'https://www.szse.cn/api/search/content'
PAGE_SIZE = 20
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0')

# URL 首段 -> 二级栏目（网站自身分类）
_L2_MAP = {
    'rules': '法律法规',
    'csrcrules': '部门规章',
    'rule': '本所业务规则',
    'service': '业务指南与流程',
    'publicadvice': '公开征求意见',
}

# URL 段序列 -> (三级, 四级) 中文名（网站自身分类；未命中走兜底，不中断采集）
_L34_MAP = {
    ('rule', 'new'): ('最新规则', ''),
    ('rule', 'all'): ('综合类', ''),
    ('rule', 'stock', 'audit'): ('股票类', '发行上市审核'),
    ('rule', 'stock', 'issue'): ('股票类', '发行承销'),
    ('rule', 'stock', 'supervision', 'currency'): ('股票类', '自律监管-通用'),
    ('rule', 'stock', 'supervision', 'mb'): ('股票类', '自律监管-主板专用'),
    ('rule', 'stock', 'supervision', 'chinext'): ('股票类', '自律监管-创业板专用'),
    ('rule', 'stock', 'trade'): ('股票类', '交易'),
    ('rule', 'bond', 'bonds', 'list'): ('债券类', '发行上市（挂牌）'),
    ('rule', 'bond', 'bonds', 'supervision'): ('债券类', '持续监管'),
    ('rule', 'bond', 'bonds', 'trade'): ('债券类', '交易'),
    ('rule', 'bond', 'abs'): ('债券类', '资产支持证券'),
    ('rule', 'fund', 'list'): ('基金类', '上市'),
    ('rule', 'fund', 'trade'): ('基金类', '交易'),
    ('rule', 'reits'): ('REITs类', ''),
    ('rule', 'derivative'): ('衍生品类', ''),
    ('rule', 'trade', 'current'): ('交易业务类', '通用'),
    ('rule', 'trade', 'business', 'margin'): ('交易业务类', '融资融券'),
    ('rule', 'trade', 'business', 'refinancing'): ('交易业务类', '转融通'),
    ('rule', 'trade', 'business', 'pledge'): ('交易业务类', '股票质押式回购'),
    ('rule', 'trade', 'business', 'price'): ('交易业务类', '质押式报价回购'),
    ('rule', 'trade', 'business', 'promise'): ('交易业务类', '约定购回'),
    ('rule', 'trade', 'business', 'transfer'): ('交易业务类', '协议转让'),
    ('rule', 'trade', 'business', 'oth'): ('交易业务类', '其他'),
    ('rule', 'memberty'): ('会员管理类', ''),
    ('rule', 'inno', 'szhk'): ('创新业务类', '深港通'),
    ('rule', 'inno', 'pilot'): ('创新业务类', '试点创新企业'),
    ('rule', 'inno', 'hc'): ('创新业务类', 'H股全流通'),
    ('rule', 'inno', 'gdr'): ('创新业务类', '互联互通存托凭证'),
    ('rule', 'pr'): ('纪律处分与内部救济类', ''),
    ('rule', 'allrules', 'bussiness'): ('规则体系', '全部业务规则'),
    ('rule', 'allrules', 'rulejoin'): ('规则体系', '规则汇编下载'),
    ('rule', 'repeal', 'announcement'): ('已废止业务规则', '规则废止公告'),
    ('rule', 'repeal', 'rules'): ('已废止业务规则', '已废止规则文本'),
    ('rules', 'law'): ('法律', ''),
    ('rules', 'regu'): ('行政法规', ''),
    ('rules', 'judicial'): ('司法解释', ''),
    ('csrcrules', 'command'): ('证监会令', ''),
    ('csrcrules', 'notice'): ('证监会公告', ''),
    ('csrcrules', 'guide'): ('监管规则适用指引', ''),
    ('service', 'share'): ('股票类', ''),
    ('service', 'bond'): ('固收类', ''),
    ('service', 'fund'): ('基金类', ''),
    ('service', 'reits'): ('REITs类', ''),
    ('service', 'derivative'): ('衍生品类', ''),
    ('service', 'member'): ('会员与交易类', ''),
    ('service', 'cross'): ('跨境创新类', ''),
    ('service', 'oth'): ('其他类', ''),
    ('publicadvice',): ('', ''),   # 二级已是 公开征求意见, 不再设三级
}


# ---------------------------------------------------------------------------
# 一、栏目清单（运行时从侧边菜单解析）
# ---------------------------------------------------------------------------
def parse_side_menu(index_html: str) -> list:
    """解析 lawrules/index.html 侧边菜单 -> [(菜单名, 绝对URL)]"""
    root = lh.fromstring(index_html)
    out = []
    for a in root.xpath('//*[contains(@class, "g-sidemenu")]//a[@href]'):
        name = (a.text_content() or '').strip()
        href = (a.get('href') or '').strip()
        if not name or not href:
            continue
        href = urljoin(SZSE_HOME, href)
        if '/lawrules/' in href and href not in {x[1] for x in out}:
            out.append((name, href))
    return out


def _lookup_levels(segs):
    """按 URL 段序列查 (三级, 四级)：先精确、再最长前缀（如 rules/law/securities -> rules/law）"""
    for n in range(len(segs), 0, -1):
        key = tuple(segs[:n])
        if key in _L34_MAP:
            return _L34_MAP[key]
    return ('', '')


def build_channel(name: str, href: str, menu_id: str = '') -> dict:
    """菜单项 -> 采集频道（层级按 URL 段规则映射，未命中兜底）"""
    path = href.split('/lawrules/', 1)[1]
    path = path.replace('.html', '').replace('/index', '').rstrip('/')
    segs = [s for s in path.split('/') if s]
    l2 = _L2_MAP.get(segs[0], '其他') if segs else '其他'
    l3, l4 = _lookup_levels(segs)
    if not l3:
        l3 = name  # 兜底: 用菜单名
    parts = [p for p in ('法律规则', l2, l3, l4) if p]
    tags = {'level_1': '法律规则', 'level_2': l2}
    if l3:
        tags['level_3'] = l3
    if l4:
        tags['level_4'] = l4
    return {
        'name': name,
        'path': path,
        'url': href,
        'menu_id': menu_id,
        'tags': tags,
        'tag_path': '/'.join(parts),
    }


# ---------------------------------------------------------------------------
# 二、列表接口
# ---------------------------------------------------------------------------
def extract_menu_id(html_text: str) -> str:
    """从栏目页内联脚本 cmsParam 中提取 currentMenuId"""
    m = re.search(r"var cmsParam\s*=\s*\{([^}]*)\}", html_text, re.S)
    if not m:
        return ''
    mm = re.search(r"currentMenuId\s*:\s*'([^']+)'", m.group(1))
    return mm.group(1) if mm else ''


def parse_api_item(item: dict, channel: dict) -> dict:
    """API 单条 -> 标准字段"""
    url = item.get('docpuburl') or ''
    if url.startswith('/'):
        url = urljoin(SZSE_HOME, url)
    ts = item.get('docpubtime') or 0
    publish_time = None
    if ts:
        from datetime import datetime
        publish_time = datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d')
    return {
        'doc_id': str(item.get('id') or ''),
        'title': (item.get('doctitle') or '').strip(),
        'publish_time': publish_time,
        'url': url,
        'navigation': item.get('navigation') or '',
        'doc_type': (item.get('doctype') or '').lower(),
        'menu_id': channel.get('menu_id', ''),
    }


def fetch_invalid_reason(html_text: str) -> str:
    """已废止详情页 var invalidReason -> 失效依据(替代规则标题)"""
    m = re.search(r"var invalidReason\s*=\s*'([^']*)'", html_text)
    return m.group(1).strip() if m and m.group(1) else ''


def has_invalid_reason_page(parsed: dict) -> bool:
    """该规则是否存在可抓取失效依据的 HTML 详情页"""
    url = (parsed.get('url') or '').lower()
    return parsed.get('doc_type') == 'html' or url.endswith(('.html', '.shtml'))


# ---------------------------------------------------------------------------
# 三、法规状态 + 组装
# ---------------------------------------------------------------------------
def rule_status_for(path: str) -> str:
    """按栏目路径动态判定法规状态（网站自身语义）"""
    if path.startswith('rule/repeal/rules'):
        return '已废止'
    if path.startswith('rule/repeal/announcement'):
        return '废止公告'
    if path.startswith('service/') or path == 'publicadvice':
        return ''  # 指南/征求意见 无法规状态
    return '现行有效'


def build_item(parsed: dict, channel: dict, invalid_reason: str = '',
               source: str = '深交所') -> dict:
    """组装最终入库字典（含层级标签 + 法规状态 + 去重 md5）"""
    from utils.tools import hash_md5
    md5_value = hash_md5(parsed['title'] + (parsed['publish_time'] or '') + parsed['url'])
    item = {
        'title': parsed['title'],
        'publish_time': parsed['publish_time'],
        'rule_status': rule_status_for(channel['path']),
        'invalid_reason': invalid_reason,
        'url': parsed['url'],
        'source': source,
        'channel_id': channel.get('menu_id', ''),
        'channel_name': channel['name'],
        'navigation': parsed.get('navigation') or '',
        'tag_path': channel['tag_path'],
        'md5_value': md5_value,
    }
    for k, v in channel['tags'].items():
        item[k] = v
    return item


# ---------------------------------------------------------------------------
# 四、爬虫
# ---------------------------------------------------------------------------
class SzseRulesSpider(BaseSpider):
    name = 'law_regulation_szse_rules'
    data_table = 'szse_rule'           # 默认库表，可用 -a table=xxx 覆盖
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
        'Referer': 'https://www.szse.cn/lawrules/',
        'User-Agent': UA,
    }
    source_name = '深交所'

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
            url=LAWRULES_INDEX, method='GET', headers=self.headers,
            callback=self.parse_index, errback=self.errback,
        )

    def parse_index(self, response):
        """侧边菜单 -> 逐栏目 -> 请求栏目页提取 menuId"""
        try:
            menu = parse_side_menu(response.text)
        except Exception as e:
            self.log_error(f'侧边菜单解析失败: {e}')
            return
        if not menu:
            self.log_error('侧边菜单为空（网站结构可能已调整）')
            return
        channels = [build_channel(name, href) for name, href in menu]
        # 「全部业务规则」与「最新规则」共用同一 menuId(全部业务规则汇总列表)，
        # 纯汇总渠道跳过；「最新规则」保留但排到最后爬——其条目与分类栏目大量重叠，
        # 分类先入库可保留分类标签，重叠条目被批内去重丢弃，仅独有条目(如修订过渡通知)入库。
        channels = [ch for ch in channels if ch['path'] != 'rule/allrules/bussiness']
        channels.sort(key=lambda c: c['path'] == 'rule/new')  # rule/new 排最后
        if self.max_channels > 0:
            channels = channels[:self.max_channels]
        self.log_info(f'法律规则栏目 {len(channels)} 个 (侧边菜单动态解析, 已跳过汇总栏目)')
        for ch in channels:
            yield scrapy.Request(
                url=ch['url'], method='GET', headers=self.headers,
                callback=self.parse_channel_page, errback=self.errback,
                cb_kwargs={'channel': ch}, dont_filter=True,
            )

    def parse_channel_page(self, response, channel):
        """栏目页 -> 提取 currentMenuId -> 请求列表接口"""
        menu_id = extract_menu_id(response.text)
        if not menu_id:
            self.log_warning(f"{channel['name']}: 页面无 cmsParam/currentMenuId -> {response.url}")
            return
        channel['menu_id'] = menu_id
        self.log_info(f"{channel['name']}: menuId={menu_id}")
        yield self._api_request(channel, 1)

    def _api_request(self, channel, page):
        return scrapy.FormRequest(
            url=API_URL, method='POST', headers=self.headers,
            formdata={
                'keyword': '', 'time': '0', 'range': 'title',
                'channelCode': channel['menu_id'],
                'currentPage': str(page), 'pageSize': str(PAGE_SIZE),
            },
            callback=self.parse_list, errback=self.errback,
            cb_kwargs={'channel': channel, 'page': page}, dont_filter=True,
        )

    def parse_list(self, response, channel, page):
        """列表接口 -> 逐条产出 + 翻页"""
        try:
            j = response.json()
        except Exception as e:
            self.log_error(f'API 返回非JSON: {response.url} {e}')
            return
        total = j.get('totalSize') or 0
        data = j.get('data') or []
        self.log_info(f"{channel['name']}: 第{page}页 {len(data)} 条 (total={total})")
        for row in data:
            parsed = parse_api_item(row, channel)
            if not parsed['title']:
                continue
            if self.fetch_detail and rule_status_for(channel['path']) == '已废止' \
                    and parsed['url'] and has_invalid_reason_page(parsed):
                yield scrapy.Request(
                    url=parsed['url'], method='GET', headers=self.headers,
                    callback=self.parse_detail, errback=self.errback,
                    cb_kwargs={'parsed': parsed, 'channel': channel}, dont_filter=True,
                )
            else:
                item = build_item(parsed, channel)
                self._collected_md5s.add(item['md5_value'])
                yield item

        if page * PAGE_SIZE < total and page < self.end_page:
            yield self._api_request(channel, page + 1)

    def parse_detail(self, response, parsed, channel):
        invalid_reason = fetch_invalid_reason(response.text)
        item = build_item(parsed, channel, invalid_reason=invalid_reason)
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
