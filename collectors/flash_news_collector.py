"""财经快讯流采集器（T1 新闻收编 · 情报部 5 源迁入）

数据源（对齐情报部 news_fetcher.py 活跃轮询源）：
  1. 新浪财经   app.cj.sina.com.cn/api/news/pc          （5s）
  2. 华尔街见闻 api-one.wallstcn.com/apiv1/content/lives （8s）
  3. Finnhub    finnhub.io/api/v1/news                   （30s，需 token）
  4. BlockBeats api.theblockbeats.news/v1/open-api/open-flash （15s）
  5. TreeOfAlpha news.treeofalpha.com/api/news           （20s）

数据落点：crawl_data.flash_news（全量落库 v6.2），字段对齐情报部 news_archive：
  news_id / text / source / tag / docurl / news_time / collected_at / md5_value

运行（独立进程，非 Scrapy）：
  python -m collectors.flash_news_collector
"""
import hashlib
import time
from datetime import datetime

import requests
from loguru import logger

from collectors.base_collector import BaseCollector

_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       'Chrome/130.0.0.0 Safari/537.36')

# 各源轮询间隔（秒）—— 与情报部一致
INTERVALS = {'sina': 5, 'wallst': 8, 'finnhub': 30, 'blockbeats': 15, 'treeofalpha': 20}


def _md5(s) -> str:
    return hashlib.md5(str(s or '').encode('utf-8', errors='ignore')).hexdigest()


def _strip_html(text: str) -> str:
    import re
    text = re.sub(r'<[^>]+>', '', text or '')
    import html as html_mod
    return html_mod.unescape(text).strip()


def _fmt(ts) -> str:
    """时间戳（秒/毫秒）或 ISO 字符串 → '%Y-%m-%d %H:%M:%S'"""
    if isinstance(ts, (int, float)):
        ts = ts / 1000 if ts > 1e12 else ts
        try:
            return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, OSError):
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    s = str(ts or '').strip().replace('T', ' ').replace('Z', '')
    return s[:19] if s else datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _row(news_id, text, source, tag='', docurl='', news_time=None) -> dict | None:
    """构造入库行；text 过短或缺失唯一键则丢弃"""
    text = _strip_html(text)
    if not text or len(text) < 6 or not news_id:
        return None
    ntime = _fmt(news_time) if news_time else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return {
        'news_id': f'{source}_{news_id}',
        'text': text[:3000],
        'source': source,
        'tag': str(tag or '')[:50],
        'docurl': str(docurl or '')[:500],
        'news_time': ntime,
        'md5_value': _md5(f'{text}|{source}|{ntime}'),
    }


# ── 各源采集实现（迁移自情报部 news_fetcher.py） ──────────────

def _poll_sina() -> list:
    try:
        r = requests.get('https://app.cj.sina.com.cn/api/news/pc',
                         params={'page': '1', 'size': '20', 'tag': '0', 'type': '0'},
                         headers={'User-Agent': _UA, 'Referer': 'https://finance.sina.com.cn/'},
                         timeout=10)
        if r.status_code != 200:
            return []
        raw = r.json().get('result', {}).get('data', {}).get('feed', {}).get('list', [])
        rows = []
        for it in raw:
            text = _strip_html(it.get('rich_text', ''))
            row = _row(it.get('id', ''), text, '新浪', it.get('tag', ''),
                       it.get('docurl', ''), it.get('create_time', ''))
            if row:
                rows.append(row)
        return rows
    except Exception as e:
        logger.debug(f'[flash_news] 新浪轮询失败: {e}')
        return []


def _poll_wallst() -> list:
    try:
        r = requests.get('https://api-one.wallstcn.com/apiv1/content/lives',
                         params={'limit': '20', 'channel': 'global-channel'},
                         headers={'User-Agent': _UA, 'Referer': 'https://wallstreetcn.com/'},
                         timeout=10)
        if r.status_code != 200:
            return []
        raw = r.json().get('data', {}).get('items', [])
        rows = []
        for it in raw:
            text = it.get('content_text', it.get('title', ''))
            row = _row(it.get('id', ''), text, '见闻', it.get('channel', ''),
                       '', it.get('display_time', ''))
            if row:
                rows.append(row)
        return rows
    except Exception as e:
        logger.debug(f'[flash_news] 华尔街见闻轮询失败: {e}')
        return []


def _poll_finnhub(token: str = '') -> list:
    if not token:
        return []
    try:
        r = requests.get(f'https://finnhub.io/api/v1/news',
                         params={'category': 'general', 'token': token}, timeout=10)
        if r.status_code != 200:
            return []
        raw = r.json()
        rows = []
        for it in (raw or [])[:20]:
            text = f"{it.get('headline', '')}. {it.get('summary', '')}"
            row = _row(it.get('id', ''), text, 'Finnhub', it.get('category', ''),
                       it.get('url', ''), it.get('datetime', ''))
            if row:
                rows.append(row)
        return rows
    except Exception as e:
        logger.debug(f'[flash_news] Finnhub 轮询失败: {e}')
        return []


def _poll_blockbeats() -> list:
    try:
        r = requests.get('https://api.theblockbeats.news/v1/open-api/open-flash',
                         params={'size': '15', 'page': '1', 'type': 'push'},
                         headers={'User-Agent': _UA}, timeout=10)
        if r.status_code != 200:
            return []
        _d = r.json().get('data', [])
        raw = _d.get('data', []) if isinstance(_d, dict) else (_d if isinstance(_d, list) else [])
        rows = []
        for it in (raw or [])[:20]:
            text = f"{it.get('title', '')} {it.get('content', '')}"
            row = _row(it.get('id', ''), text, 'blockbeats', 'crypto',
                       it.get('url', ''), it.get('create_time', ''))
            if row:
                rows.append(row)
        return rows
    except Exception as e:
        logger.debug(f'[flash_news] BlockBeats 轮询失败: {e}')
        return []


def _poll_treeofalpha() -> list:
    try:
        r = requests.get('https://news.treeofalpha.com/api/news',
                         params={'limit': '10'}, headers={'User-Agent': _UA}, timeout=10)
        if r.status_code != 200:
            return []
        raw = r.json()
        rows = []
        for it in (raw or [])[:15]:
            title = _strip_html(str(it.get('title', '')))
            summary = _strip_html(str(it.get('summary', '')))
            text = f'{title}. {summary}' if summary else title
            row = _row(it.get('id', it.get('time', 0)), text, 'treeofalpha', 'crypto',
                       it.get('url', ''), it.get('time', ''))
            if row:
                rows.append(row)
        return rows
    except Exception as e:
        logger.debug(f'[flash_news] TreeOfAlpha 轮询失败: {e}')
        return []


class FlashNewsCollector(BaseCollector):
    """财经快讯流采集器：多源轮询（各自间隔）→ 每源一表（news_<source>，v6.3 §10.46 细分）"""

    name = 'flash_news'
    data_table = 'flash_news'  # 兼容占位；实际落 news_sina/news_wallst/... 各源表
    poll_interval = 5  # 主循环粒度 = 最短源间隔（新浪 5s）；各源按自身间隔跳数

    # 源 → 细分表名
    SOURCE_TABLE = {
        'sina': 'news_sina',
        'wallst': 'news_wallst',
        'finnhub': 'news_finnhub',
        'blockbeats': 'news_blockbeats',
        'treeofalpha': 'news_treeofalpha',
    }

    # 通用快讯表 DDL（`{table}` 占位 → 每源建表）
    table_ddl = """
    CREATE TABLE IF NOT EXISTS `{table}` (
      `id` BIGINT NOT NULL AUTO_INCREMENT,
      `news_id` VARCHAR(64) NOT NULL COMMENT '源ID（带来源前缀，如 sina_123）',
      `text` TEXT NOT NULL COMMENT '快讯文本',
      `source` VARCHAR(30) NOT NULL COMMENT '来源：新浪/见闻/Finnhub/blockbeats/treeofalpha',
      `tag` VARCHAR(50) DEFAULT '' COMMENT '标签',
      `docurl` VARCHAR(500) DEFAULT '' COMMENT '原文链接',
      `news_time` DATETIME NOT NULL COMMENT '源发布时间',
      `collected_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      `md5_value` VARCHAR(64) NOT NULL COMMENT '去重键（text|source|time）',
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_md5` (`md5_value`),
      KEY `ix_source` (`source`),
      KEY `ix_news_time` (`news_time`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='财经快讯流（T1 新闻收编 · 按源细分）'
    """

    def __init__(self, finnhub_token: str = '', **kwargs):
        super().__init__(**kwargs)
        self._finnhub_token = finnhub_token
        # 每源轮询节拍：tick 计数
        self._tick = 0
        self._sources = {
            'sina': (_poll_sina, INTERVALS['sina']),
            'wallst': (_poll_wallst, INTERVALS['wallst']),
            'finnhub': (lambda: _poll_finnhub(self._finnhub_token), INTERVALS['finnhub']),
            'blockbeats': (_poll_blockbeats, INTERVALS['blockbeats']),
            'treeofalpha': (_poll_treeofalpha, INTERVALS['treeofalpha']),
        }

    def poll_once(self) -> list:
        """一个主循环周期：按源间隔跳数轮询到期的源，按源分表落库"""
        self._tick += 1
        for src, (poll_fn, interval) in self._sources.items():
            if self._tick % interval == 0 or self._tick == 1:
                try:
                    rows = poll_fn() or []
                    if rows:
                        table = self.SOURCE_TABLE.get(src, 'flash_news')
                        self._persist_to(table, rows)
                        logger.info(f'[flash_news] {src} → {table}: +{len(rows)} 行')
                except Exception as e:
                    logger.warning(f'[flash_news] 源 {src} 异常: {e}')
        return []  # 已按源落库，主循环无需再统一落库

    def _table_ddl_for(self, table: str) -> str:
        return self.table_ddl.format(table=table)


def main():
    import os
    import sys

    # 允许从 crawl 平台根目录运行：python -m collectors.flash_news_collector
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    token = os.environ.get('FINNHUB_API_KEY', '')
    if not token:
        logger.warning('[flash_news] 未设置 FINNHUB_API_KEY，Finnhub 源跳过')

    collector = FlashNewsCollector(finnhub_token=token)
    try:
        collector.start()
    except KeyboardInterrupt:
        logger.info('[flash_news] 收到退出信号，停止采集')
        collector.stop()


if __name__ == '__main__':
    main()
