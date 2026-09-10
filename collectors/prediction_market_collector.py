"""预测市场数据采集器（Polymarket / Kalshi / Manifold）

数据源（全部公开只读，无需密钥）：
  - Polymarket Gamma API : https://gamma-api.polymarket.com/markets
      加密/宏观/政治事件的隐含概率；outcomes/outcomePrices 为 JSON 字符串
  - Kalshi               : https://api.elections.kalshi.com/trade-api/v2/markets
      受 CFTC 监管的事件合约（Fed/CPI/GDP/选举），价格为美分
  - Manifold             : https://api.manifold.markets/v0/markets
      社区预测市场，probability 直接给出

数据落点：crawl_data.prediction_markets（按小时快照，全量落库 v6.2）。
出网：走 base_collector.get_proxies()（CRAWL_OUTBOUND_PROXY → 152 本地桥 → VPS SOCKS5）。

运行（独立进程，非 Scrapy）：
  python -m collectors.prediction_market_collector
环境变量：
  PM_SOURCES=polymarket,kalshi,manifold   # 启用的数据源
  PM_LIMIT=300                            # 每源单次抓取条数
  PM_MIN_VOLUME=1000                      # 成交量下限（过滤噪声市场）
"""
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests
from loguru import logger

from collectors.base_collector import BaseCollector, get_proxies

_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36')

PM_SOURCES = [s.strip() for s in os.getenv('PM_SOURCES', 'polymarket,kalshi').split(',') if s.strip()]
PM_LIMIT = int(os.getenv('PM_LIMIT', '100'))
PM_MIN_VOLUME = float(os.getenv('PM_MIN_VOLUME', '1000'))
# 152→VPS 链路对大响应不稳定（实测 >400KB 时常截断），Kalshi 按系列小批量抓取
PM_KALSHI_SERIES = [s.strip() for s in os.getenv(
    'PM_KALSHI_SERIES', 'KXFED,KXCPI,KXPAYROLLS,KXGDP,KXRECSSNBER').split(',') if s.strip()]

PM_URL = 'https://gamma-api.polymarket.com/markets'
KALSHI_URL = 'https://api.elections.kalshi.com/trade-api/v2/markets'
MANIFOLD_URL = 'https://api.manifold.markets/v0/markets'


def _hour_ts() -> str:
    """当前小时（UTC）→ 'YYYY-MM-DD HH:00:00'，同小时重复抓取只保留一条快照"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:00:00')


def _f(v, default=0.0) -> float:
    try:
        if v in (None, ''):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _row(source: str, market_id: str, question: str, yes_prob, volume, liquidity,
         category: str, end_date: str, url: str, raw: dict, hour: str) -> dict | None:
    if not market_id or not question:
        return None
    prob = _f(yes_prob, -1.0)
    if prob < 0:
        return None
    if prob > 1.0:  # 美分制（Kalshi）
        prob = prob / 100.0
    md5 = hashlib.md5(f'{source}|{market_id}|{hour}'.encode()).hexdigest()
    return {
        'source': source,
        'market_id': str(market_id)[:80],
        'question': question[:500],
        'category': (category or '')[:80],
        'yes_prob': round(prob, 6),
        'volume_usd': round(_f(volume), 2),
        'liquidity_usd': round(_f(liquidity), 2),
        'end_date': (end_date or '')[:40],
        'url': (url or '')[:500],
        'payload': json.dumps(raw, ensure_ascii=False)[:6000],
        'ts': hour,
        'md5_value': md5,
    }


class PredictionMarketCollector(BaseCollector):
    """预测市场隐含概率 + 成交量 → crawl_data.prediction_markets"""

    name = 'prediction_market'
    data_table = 'prediction_markets'
    poll_interval = 600  # 10 分钟

    table_ddl = """
    CREATE TABLE IF NOT EXISTS `prediction_markets` (
      `id` BIGINT NOT NULL AUTO_INCREMENT,
      `source` VARCHAR(20) NOT NULL COMMENT 'polymarket/kalshi/manifold',
      `market_id` VARCHAR(80) NOT NULL COMMENT '市场ID',
      `question` VARCHAR(500) NOT NULL COMMENT '市场问题',
      `category` VARCHAR(80) DEFAULT '' COMMENT '分类',
      `yes_prob` DECIMAL(10,6) NOT NULL COMMENT 'YES 隐含概率 0-1',
      `volume_usd` DECIMAL(18,2) DEFAULT 0 COMMENT '累计成交量(USD)',
      `liquidity_usd` DECIMAL(18,2) DEFAULT 0 COMMENT '流动性(USD)',
      `end_date` VARCHAR(40) DEFAULT '' COMMENT '结算时间',
      `url` VARCHAR(500) DEFAULT '' COMMENT '市场链接',
      `payload` TEXT COMMENT '原始 JSON',
      `ts` DATETIME NOT NULL COMMENT '快照小时(UTC)',
      `md5_value` VARCHAR(64) NOT NULL COMMENT '去重键(source|market_id|hour)',
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_md5` (`md5_value`),
      KEY `ix_source_ts` (`source`, `ts`),
      KEY `ix_prob` (`yes_prob`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预测市场概率快照（Polymarket/Kalshi/Manifold）'
    """

    def __init__(self, sources=None, **kwargs):
        super().__init__(**kwargs)
        self.sources = [s.lower() for s in (sources or PM_SOURCES)]
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': _UA, 'Accept': 'application/json'})

    # ── 采集 ──────────────────────────────────────────────────

    def poll_once(self) -> list:
        hour = _hour_ts()
        rows = []
        for src in self.sources:
            try:
                if src == 'polymarket':
                    rows += self._polymarket(hour)
                elif src == 'kalshi':
                    rows += self._kalshi(hour)
                elif src == 'manifold':
                    rows += self._manifold(hour)
                else:
                    logger.warning(f'[prediction_market] 未知数据源: {src}')
            except Exception as e:
                logger.warning(f'[prediction_market] {src} 采集异常: {str(e)[:160]}')
        logger.info(f'[prediction_market] 本轮 {len(rows)} 个市场快照 (hour={hour})')
        return rows

    def _get(self, url, params=None, tries: int = 3):
        """带重试的 GET：152→VPS 链路偶发截断，重试可显著降低失败率"""
        last = None
        for attempt in range(1, tries + 1):
            try:
                r = self.session.get(url, params=params, proxies=get_proxies(), timeout=30)
                r.raise_for_status()
                return r.json()
            except Exception as e:
                last = e
                if attempt < tries:
                    time.sleep(1.5 * attempt)
        raise last

    def _polymarket(self, hour: str) -> list:
        data = self._get(PM_URL, {
            'closed': 'false', 'limit': PM_LIMIT,
            'order': 'volumeNum', 'ascending': 'false',
        })
        if isinstance(data, dict):
            data = data.get('data') or data.get('markets') or []
        out = []
        for m in data or []:
            vol = _f(m.get('volumeNum') or m.get('volume'), 0)
            if vol < PM_MIN_VOLUME:
                continue
            # outcomes / outcomePrices 是 JSON 字符串，取第一个结果作为 YES
            prob = None
            try:
                outs = m.get('outcomes')
                prices = m.get('outcomePrices')
                outs = json.loads(outs) if isinstance(outs, str) else (outs or [])
                prices = json.loads(prices) if isinstance(prices, str) else (prices or [])
                if outs and prices and str(outs[0]).strip().lower() in ('yes', 'true'):
                    prob = _f(prices[0], -1)
                elif prices:
                    prob = _f(prices[0], -1)
            except Exception:
                prob = None
            slug = m.get('slug') or ''
            row = _row('polymarket', m.get('id'), m.get('question'), prob, vol,
                       m.get('liquidityNum') or m.get('liquidity'),
                       m.get('category') or (m.get('groupSlug') or ''),
                       m.get('endDate'), f'https://polymarket.com/event/{slug}' if slug else '',
                       m, hour)
            if row:
                out.append(row)
        return out

    def _kalshi(self, hour: str) -> list:
        """Kalshi：按宏观系列小批量抓取（大列表易被链路截断），字段为 *_dollars / *_fp"""
        out = []
        seen = set()
        for series in PM_KALSHI_SERIES:
            try:
                data = self._get(KALSHI_URL, {
                    'limit': min(PM_LIMIT, 200), 'status': 'open', 'series_ticker': series})
            except Exception as e:
                logger.warning(f'[prediction_market] kalshi {series} 抓取失败: {str(e)[:100]}')
                continue
            markets = (data or {}).get('markets', []) if isinstance(data, dict) else []
            for m in markets:
                ticker = m.get('ticker') or ''
                if not ticker or ticker in seen or 'MVE' in ticker.upper():
                    continue
                if (m.get('market_type') or 'binary') not in ('binary', ''):
                    continue
                vol = _f(m.get('volume_fp') or m.get('volume_24h_fp'), 0)
                oi = _f(m.get('open_interest_fp') or m.get('open_interest'), 0)
                liq = _f(m.get('liquidity_dollars') or m.get('liquidity'), 0)
                if max(vol, oi, liq) < PM_MIN_VOLUME:
                    continue
                bid = _f(m.get('yes_bid_dollars') if m.get('yes_bid_dollars') is not None
                         else m.get('yes_bid'), -1)
                ask = _f(m.get('yes_ask_dollars') if m.get('yes_ask_dollars') is not None
                         else m.get('yes_ask'), -1)
                last = _f(m.get('last_price_dollars') if m.get('last_price_dollars') is not None
                          else m.get('last_price'), -1)
                prob = (bid + ask) / 2 if (bid > 0 and ask > 0) else last
                row = _row('kalshi', ticker, m.get('title') or m.get('subtitle'), prob,
                           vol or oi, liq, series,
                           m.get('close_time') or m.get('expiration_time'),
                           f'https://kalshi.com/markets/{ticker}' if ticker else '',
                           m, hour)
                if row:
                    seen.add(ticker)
                    out.append(row)
        return out

    def _manifold(self, hour: str) -> list:
        data = self._get(MANIFOLD_URL, {'limit': min(PM_LIMIT, 1000)})
        if isinstance(data, dict):
            data = data.get('markets') or []
        out = []
        for m in data or []:
            if m.get('isResolved') or m.get('outcomeType') not in (None, 'BINARY'):
                continue
            vol = _f(m.get('volume'), 0)
            if vol < PM_MIN_VOLUME:
                continue
            row = _row('manifold', m.get('id'), m.get('question'), m.get('probability'),
                       vol, _f(m.get('totalLiquidity'), 0), m.get('groupSlug') or '',
                       m.get('closeTime'), m.get('url'), m, hour)
            if row:
                out.append(row)
        return out


def main():
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    collector = PredictionMarketCollector()
    try:
        collector.start()
    except KeyboardInterrupt:
        logger.info('[prediction_market] 收到退出信号')
        collector.stop()


if __name__ == '__main__':
    main()
