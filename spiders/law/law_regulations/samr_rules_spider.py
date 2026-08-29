# -*- coding: utf-8 -*-
"""
市场监管总局官网「法律法规」栏目 采集爬虫 (单文件: 解析逻辑+爬虫)
================================================================
采集范围：https://www.samr.gov.cn/zw/flfg/ 下 法律(/zw/flfg/fl/) 与
行政法规(/zw/flfg/xzfg/) 两个子栏目（法律法规栏目 = 两者合集），
输出 一级~三级 层级标签。

自适应设计（网站变动不失效）：
  · 栏目页面 id(ColId) 及站点 webId/tplSetId 每次运行从页面 <meta name="ColId"> 与
    unitbuild 脚本 queryData 动态提取，不写死任何栏目 id；
  · 列表走 CMS 渲染接口（与页面 JS 完全一致）：
    GET /api-gateway/jpaas-publish-server/front/page/build/unit
    参数: webId/tplSetId/parseType/pageType/tagId/editType/pageId
          + paramJson={"pageNo":N,"pageSize":20}
    响应: {data:{html: 列表HTML}}，条目 <a title>标题</a> + 日期；
  · 法规状态：本站详情页无 时效性/状态 标记，故不做状态字段（仅列标题/日期/链接）。

用法（本地冒烟测试，不写库）：
    scrapy crawl law_regulation_samr_rules -O samr_rules.json \
        -s ITEM_PIPELINES={} -s LOG_LEVEL=INFO
用法（正式入库，库表默认 samr_rule）：
    scrapy crawl law_regulation_samr_rules -a table=samr_rule
    scrapy crawl law_regulation_samr_rules -a reconcile=1   # 下线对账
分页控制：-a start_page=1 -a end_page=100
"""
import json
import re
import scrapy
from urllib.parse import urljoin

from spiders.base_spider import BaseSpider
from lxml import html as lh

SAMR_HOME = 'https://www.samr.gov.cn'
BUILD_API = 'https://www.samr.gov.cn/api-gateway/jpaas-publish-server/front/page/build/unit'
PAGE_SIZE = 20

# 法律法规栏目子栏目: (显示名, 页面路径)
CHANNELS = [
    ('法律', '/zw/flfg/fl/index.html'),
    ('行政法规', '/zw/flfg/xzfg/index.html'),
]


# ---------------------------------------------------------------------------
# 一、站点/栏目配置（运行时动态提取）
# ---------------------------------------------------------------------------
def extract_site_config(page_html: str) -> dict:
    """从栏目页 unitbuild 脚本 queryData 提取 webId/tplSetId，从 ColId meta 提取 pageId"""
    conf = {}
    m = re.search(r"id=\"select_main\"", page_html)  # 无关占位，防止空匹配
    m = re.search(r"queryData=\"\{'parseType':'bulidstatic','webId':'([0-9a-f]{32})',"
                  r"'tplSetId':'([0-9a-f]{32})'", page_html)
    if m:
        conf['webId'] = m.group(1)
        conf['tplSetId'] = m.group(2)
    m = re.search(r'name="ColId" content="([0-9a-f]{32})"', page_html)
    if m:
        conf['pageId'] = m.group(1)
    return conf


def build_api_params(conf: dict, page_no: int) -> dict:
    """构造列表接口查询参数（与页面 JS 一致）"""
    return {
        'webId': conf['webId'],
        'tplSetId': conf['tplSetId'],
        'parseType': 'bulidstatic',
        'pageType': 'column',
        'tagId': '内容区域',
        'editType': 'null',
        'pageId': conf['pageId'],
        'paramJson': json.dumps({'pageNo': page_no, 'pageSize': PAGE_SIZE}),
    }


# ---------------------------------------------------------------------------
# 二、列表解析
# ---------------------------------------------------------------------------
def parse_list_html(html_text: str) -> list:
    """解析接口返回 data.html -> [{title, publish_time, url}]"""
    items = []
    root = lh.fromstring(html_text)
    for li in root.xpath('//li[contains(@class, "nav04Left02_content")]/a[@href]'):
        title = (li.get('title') or '').strip() or (li.text_content() or '').strip()
        href = (li.get('href') or '').strip()
        if not title or not href:
            continue
        # 日期在相邻 li.nav04Left02_contenttime
        date = ''
        parent = li.getparent()
        if parent is not None:
            nxt = parent.getnext()
            if nxt is not None and 'contenttime' in (nxt.get('class') or ''):
                date = (nxt.text_content() or '').strip()
        items.append({
            'title': title,
            'publish_time': date or None,
            'url': href if href.startswith('http') else urljoin(SAMR_HOME, href),
        })
    return items


def extract_pagination(html_text: str) -> dict:
    """从 data.html 分页节点提取 count（总数）"""
    m = re.search(r'count="(\d+)"', html_text)
    return {'count': int(m.group(1)) if m else 0}


# ---------------------------------------------------------------------------
# 三、组装
# ---------------------------------------------------------------------------
def build_item(parsed: dict, channel: tuple, conf: dict, source: str = '市场监管总局') -> dict:
    """组装最终入库字典（含层级标签 + 去重 md5）"""
    from utils.tools import hash_md5
    title = parsed['title']
    publish_time = (parsed.get('publish_time') or '').strip() or None
    md5_value = hash_md5(title + (publish_time or '') + parsed['url'])
    tags = {'level_1': '市场监管总局', 'level_2': '法律法规', 'level_3': channel[0]}
    return {
        'title': title,
        'publish_time': publish_time,
        'url': parsed['url'],
        'source': source,
        'channel_id': conf.get('pageId', ''),
        'channel_name': channel[0],
        'tag_path': '市场监管总局/法律法规/' + channel[0],
        'md5_value': md5_value,
        'level_1': '市场监管总局',
        'level_2': '法律法规',
        'level_3': channel[0],
    }


# ---------------------------------------------------------------------------
# 四、爬虫
# ---------------------------------------------------------------------------
class SamrRulesSpider(BaseSpider):
    name = 'law_regulation_samr_rules'
    data_table = 'samr_rule'           # 默认库表，可用 -a table=xxx 覆盖
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
        'Referer': 'https://www.samr.gov.cn/',
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                       '(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0'),
    }
    source_name = '市场监管总局'

    def __init__(self, start_page=None, end_page=None, jobid=None, table=None,
                 reconcile=None, **kwargs):
        super().__init__(start_page=start_page, end_page=end_page, jobid=jobid, **kwargs)
        if table:
            self.data_table = table
        self.reconcile = str(reconcile or '0') in ('1', 'true', 'yes')
        self._collected_md5s = set()
        self._request_errors = 0

    def start_requests(self):
        for name, path in CHANNELS:
            page_url = f'{SAMR_HOME}{path}'
            yield scrapy.Request(
                url=page_url, method='GET', headers=self.headers,
                callback=self.parse_channel_page, errback=self.errback,
                cb_kwargs={'channel': (name, path)}, dont_filter=True,
            )

    def parse_channel_page(self, response, channel):
        """栏目页 -> 提取站点配置 -> 请求列表接口第1页"""
        conf = extract_site_config(response.text)
        if not conf.get('webId') or not conf.get('pageId'):
            self.log_warning(f"{channel[0]}: 站点配置提取失败 -> {response.url}")
            return
        self.log_info(f"{channel[0]}: webId={conf['webId'][:8]} pageId={conf['pageId'][:8]}")
        yield self._api_request(conf, channel, 1)

    def _api_request(self, conf, channel, page_no):
        return scrapy.Request(
            url=BUILD_API + '?' + '&'.join(
                f'{k}={v}' for k, v in build_api_params(conf, page_no).items()),
            method='GET', headers=self.headers,
            callback=self.parse_list, errback=self.errback,
            cb_kwargs={'conf': conf, 'channel': channel, 'page_no': page_no},
            dont_filter=True,
        )

    def parse_list(self, response, conf, channel, page_no):
        """列表接口 -> 逐条产出 + 翻页"""
        try:
            j = response.json()
            html = (j.get('data') or {}).get('html') or ''
        except Exception as e:
            self.log_error(f'接口返回异常: {response.url} {e}')
            return
        items = parse_list_html(html)
        total = extract_pagination(html).get('count', 0)
        self.log_info(f"{channel[0]}: 第{page_no}页 {len(items)} 条 (total={total})")
        for parsed in items:
            item = build_item(parsed, channel, conf, source=self.source_name)
            self._collected_md5s.add(item['md5_value'])
            yield item
        # 翻页
        if page_no * PAGE_SIZE < total and page_no < self.end_page:
            yield self._api_request(conf, channel, page_no + 1)

    def errback(self, failure):
        self._request_errors += 1
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')

    def closed(self, reason):
        """下线对账: -a reconcile=1 时，将本批未采集到的旧记录状态置为 已下线"""
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
