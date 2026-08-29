"""OKX Taker 成交量采集器（T2 收编 C3 · 交易部 taker_flow.py 迁入）

数据源：OKX 公共 REST（无需密钥）：
  - /market/trades  最近成交（含 side，聚合统计 taker 买卖量比）

注：OKX v5 无 /market/taker-volume REST 端点（taker 数据走 WS books/trades），
REST 侧以最近成交按 side 聚合作近似；实时版本后续接 WS。

数据落点：crawl_data.taker_flow（全量落库 v6.2）。

运行（独立进程，非 Scrapy）：
  python -m collectors.taker_flow_collector
  环境变量：TAKER_SYMBOLS=BTC-USDT,ETH-USDT
"""
import os
import time
from datetime import datetime

import requests
from loguru import logger

from collectors.base_collector import BaseCollector

_OKX_BASE = 'https://www.okx.com/api/v5'
_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0'

DEFAULT_SYMBOLS = os.getenv('TAKER_SYMBOLS', 'BTC-USDT,ETH-USDT').split(',')


class TakerFlowCollector(BaseCollector):
    """OKX 最近成交 taker 买卖量 → crawl_data.taker_flow"""

    name = 'taker_flow'
    data_table = 'taker_flow'
    poll_interval = 60  # 60s 轮询

    table_ddl = """
    CREATE TABLE IF NOT EXISTS `taker_flow` (
      `id` BIGINT NOT NULL AUTO_INCREMENT,
      `symbol` VARCHAR(20) NOT NULL COMMENT 'BTC-USDT',
      `data_type` VARCHAR(20) NOT NULL COMMENT 'taker_flow',
      `payload` TEXT NOT NULL COMMENT '买卖量聚合 JSON',
      `ts` DATETIME NOT NULL COMMENT '采集时间',
      `md5_value` VARCHAR(64) NOT NULL COMMENT '去重键（symbol|ts）',
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_md5` (`md5_value`),
      KEY `ix_symbol_ts` (`symbol`, `ts`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='OKX taker 成交量流（T2 收编 C3）'
    """

    def __init__(self, symbols=None, **kwargs):
        super().__init__(**kwargs)
        self.symbols = [s.strip() for s in (symbols or DEFAULT_SYMBOLS) if s.strip()]

    def poll_once(self) -> list:
        rows = []
        for sym in self.symbols:
            try:
                rows += self._fetch_taker(sym)
            except Exception as e:
                logger.warning(f'[taker_flow] {sym} 异常: {e}')
        return rows

    def _fetch_taker(self, symbol: str) -> list:
        """最近成交按 side 聚合：buy_vol/sell_vol/buy_sell_ratio"""
        r = requests.get(f'{_OKX_BASE}/market/trades',
                         params={'instId': symbol, 'limit': '200'},
                         headers={'User-Agent': _UA}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get('code') != '0':
            raise RuntimeError(f"OKX error: {data.get('msg')}")
        trades = data.get('data') or []
        buy_vol = sum(float(t.get('sz', 0)) for t in trades if t.get('side') == 'buy')
        sell_vol = sum(float(t.get('sz', 0)) for t in trades if t.get('side') == 'sell')
        total = buy_vol + sell_vol
        payload = {
            'trades': len(trades),
            'buy_vol': round(buy_vol, 8),
            'sell_vol': round(sell_vol, 8),
            'buy_sell_ratio': round(buy_vol / sell_vol, 4) if sell_vol > 0 else None,
            'ts_first': trades[0].get('ts') if trades else None,
        }
        import json as _json
        ts = int(time.time() * 1000)
        md5 = __import__('hashlib').md5(f'{symbol}|{ts}'.encode()).hexdigest()
        return [{
            'symbol': symbol,
            'data_type': 'taker_flow',
            'payload': _json.dumps(payload, ensure_ascii=False),
            'ts': _fmt_ts(ts),
            'md5_value': md5,
        }]


def _fmt_ts(ts) -> str:
    try:
        ts = int(ts)
        ts = ts / 1000 if ts > 1e12 else ts
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, OSError, TypeError):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def main():
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    collector = TakerFlowCollector()
    try:
        collector.start()
    except KeyboardInterrupt:
        logger.info('[taker_flow] 收到退出信号')
        collector.stop()


if __name__ == '__main__':
    main()
