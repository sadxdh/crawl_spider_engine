"""交易所行情流采集器（T2 行情收编 · 交易部 OKX 公共行情迁入）

数据源：OKX 公共 REST API（无需密钥）：
  - ticker        https://www.okx.com/api/v5/market/ticker?instId={inst}
  - candles       https://www.okx.com/api/v5/market/candles?instId={inst}&bar=5m&limit=1
  - funding       https://www.okx.com/api/v5/public/funding-rate?instId={inst}
  - open-interest https://www.okx.com/api/v5/public/open-interest?instId={inst}

数据落点：crawl_data.market_data（全量落库 v6.2；ticker/funding/oi 为最新快照，
candles 按时间点追加）。实时消费走事件总线（crawl.market.quote，T2 后续），
历史回测/分析读 market_data。

运行（独立进程，非 Scrapy）：
  python -m collectors.market_collector
  环境变量：MARKET_INST_IDS=BTC-USDT-SWAP,ETH-USDT-SWAP（逗号分隔，默认 BTC/ETH 永续）
"""
import os
import time
from datetime import datetime

import requests
from loguru import logger

from collectors.base_collector import BaseCollector

_OKX_BASE = 'https://www.okx.com/api/v5'
_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0'

DEFAULT_INSTS = os.getenv('MARKET_INST_IDS', 'BTC-USDT-SWAP,ETH-USDT-SWAP').split(',')


def _get(path: str, params: dict) -> dict:
    r = requests.get(f'{_OKX_BASE}{path}', params=params,
                     headers={'User-Agent': _UA}, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data.get('code') != '0':
        raise RuntimeError(f"OKX API error: {data.get('msg')}")
    return data['data']


class MarketCollector(BaseCollector):
    """交易所公共行情采集器：ticker/candles/funding/oi → crawl_data.market_data"""

    name = 'market_quote'
    data_table = 'market_data'
    poll_interval = 60  # 公共行情 60s 轮询（实时微观走 WS 后续版本）

    table_ddl = """
    CREATE TABLE IF NOT EXISTS `market_data` (
      `id` BIGINT NOT NULL AUTO_INCREMENT,
      `inst_id` VARCHAR(30) NOT NULL COMMENT '合约/标的，如 BTC-USDT-SWAP',
      `data_type` VARCHAR(20) NOT NULL COMMENT 'ticker/candle/funding/oi',
      `asset` VARCHAR(20) NOT NULL COMMENT '品种：BTC/ETH/...',
      `payload` TEXT NOT NULL COMMENT '行情 JSON',
      `ts` DATETIME NOT NULL COMMENT '行情时间（OKX ts 或采集时间）',
      `md5_value` VARCHAR(64) NOT NULL COMMENT '去重键（inst|type|ts）',
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_md5` (`md5_value`),
      KEY `ix_inst_type` (`inst_id`, `data_type`),
      KEY `ix_ts` (`ts`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交易所公共行情流（T2 收编）'
    """

    def __init__(self, inst_ids=None, **kwargs):
        super().__init__(**kwargs)
        self.inst_ids = [i.strip() for i in (inst_ids or DEFAULT_INSTS) if i.strip()]

    def poll_once(self) -> list:
        """单轮：拉全部标的的 ticker + candles + funding + oi + mark_price + order_book"""
        rows = []
        for inst in self.inst_ids:
            asset = inst.split('-')[0]
            try:
                rows += self._fetch_ticker(inst, asset)
                rows += self._fetch_candles(inst, asset)
                rows += self._fetch_funding(inst, asset)
                rows += self._fetch_oi(inst, asset)
                rows += self._fetch_mark_price(inst, asset)
                rows += self._fetch_order_book(inst, asset)
            except Exception as e:
                logger.warning(f'[market_quote] {inst} 采集异常: {e}')
        return rows

    # ── 各数据类型 ─────────────────────────────────────────────

    def _row(self, inst: str, asset: str, data_type: str, payload: dict, ts_ts) -> dict | None:
        import json as _json
        ts = _fmt_ts(ts_ts)
        md5 = __import__('hashlib').md5(f'{inst}|{data_type}|{ts}'.encode()).hexdigest()
        return {
            'inst_id': inst,
            'data_type': data_type,
            'asset': asset,
            'payload': _json.dumps(payload, ensure_ascii=False),
            'ts': ts,
            'md5_value': md5,
        }

    def _fetch_ticker(self, inst, asset) -> list:
        data = _get('/market/ticker', {'instId': inst})
        rows = []
        for t in data:
            ts = t.get('ts', int(time.time() * 1000))
            rows.append(self._row(inst, asset, 'ticker', t, ts))
        return [r for r in rows if r]

    def _fetch_candles(self, inst, asset) -> list:
        data = _get('/market/candles', {'instId': inst, 'bar': '5m', 'limit': '1'})
        rows = []
        for c in data:
            # OKX candle: [ts, o, h, l, c, vol, volCcy, ...]
            ts = int(c[0])
            payload = {'ts': c[0], 'o': c[1], 'h': c[2], 'l': c[3],
                       'c': c[4], 'vol': c[5], 'volCcy': c[6]}
            rows.append(self._row(inst, asset, 'candle', payload, ts))
        return [r for r in rows if r]

    def _fetch_funding(self, inst, asset) -> list:
        data = _get('/public/funding-rate', {'instId': inst})
        rows = []
        for f in data:
            ts = f.get('fundingTime', int(time.time() * 1000))
            rows.append(self._row(inst, asset, 'funding', f, ts))
        return [r for r in rows if r]

    def _fetch_oi(self, inst, asset) -> list:
        data = _get('/public/open-interest', {'instId': inst})
        rows = []
        for o in data:
            ts = o.get('ts', int(time.time() * 1000))
            rows.append(self._row(inst, asset, 'oi', o, ts))
        return [r for r in rows if r]

    def _fetch_mark_price(self, inst, asset) -> list:
        """标记价格（liq_monitor 等清算分析用）"""
        data = _get('/public/mark-price', {'instId': inst})
        rows = []
        for m in data:
            ts = m.get('ts', int(time.time() * 1000))
            rows.append(self._row(inst, asset, 'mark_price', m, ts))
        return [r for r in rows if r]

    def _fetch_order_book(self, inst, asset) -> list:
        """订单簿快照（前 20 档，liq_monitor 深度分析用）"""
        data = _get('/market/books', {'instId': inst, 'sz': '20'})
        rows = []
        for ob in data:
            ts = ob.get('ts', int(time.time() * 1000))
            # 只保留前 5 档防 payload 过大（深度分析用足够）
            slim = {'ts': ob.get('ts'), 'asks': (ob.get('asks') or [])[:5],
                    'bids': (ob.get('bids') or [])[:5]}
            rows.append(self._row(inst, asset, 'order_book', slim, ts))
        return [r for r in rows if r]


def _fmt_ts(ts) -> str:
    """OKX 毫秒时间戳 → '%Y-%m-%d %H:%M:%S'"""
    try:
        ts = int(ts)
        ts = ts / 1000 if ts > 1e12 else ts
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, OSError, TypeError):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def main():
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    collector = MarketCollector()
    try:
        collector.start()
    except KeyboardInterrupt:
        logger.info('[market_quote] 收到退出信号')
        collector.stop()


if __name__ == '__main__':
    main()
