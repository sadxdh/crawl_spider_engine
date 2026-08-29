"""COMEX 黄金行情采集器（T2 收编 C3 · 交易部 gold.py 迁入）

数据源：Stooq 公开 CSV（无需密钥/额外依赖，替代原 yfinance）：
  - https://stooq.com/q/d/l/?s=gc.f&i=d   日 K（COMEX 黄金期货 GC=F）
  - https://stooq.com/q/l/?s=gc.f&f=sd2t2ohlcv&h&e=csv  最新快照

数据落点：crawl_data.gold_market（全量落库 v6.2）。

运行（独立进程，非 Scrapy）：
  python -m collectors.gold_collector
  环境变量：GOLD_SYMBOL=gc.f（stooq 代码）；GOLD_CANDLES=60
"""
import os
import time
from datetime import datetime

import requests
from loguru import logger

from collectors.base_collector import BaseCollector

_STOOQ_DAILY = 'https://stooq.com/q/d/l/'
_STOOQ_LATEST = 'https://stooq.com/q/l/'
_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0'

GOLD_SYMBOL = os.getenv('GOLD_SYMBOL', 'gc.f')
GOLD_CANDLES = int(os.getenv('GOLD_CANDLES', '60'))


class GoldCollector(BaseCollector):
    """COMEX 黄金期货：ticker + candles → crawl_data.gold_market"""

    name = 'gold_market'
    data_table = 'gold_market'
    poll_interval = 300  # 黄金 5min 轮询

    table_ddl = """
    CREATE TABLE IF NOT EXISTS `gold_market` (
      `id` BIGINT NOT NULL AUTO_INCREMENT,
      `symbol` VARCHAR(20) NOT NULL COMMENT 'gc.f',
      `data_type` VARCHAR(20) NOT NULL COMMENT 'ticker/candle',
      `payload` TEXT NOT NULL COMMENT '行情 JSON',
      `ts` DATETIME NOT NULL COMMENT '行情时间或采集时间',
      `md5_value` VARCHAR(64) NOT NULL COMMENT '去重键（symbol|type|ts）',
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_md5` (`md5_value`),
      KEY `ix_type_ts` (`data_type`, `ts`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='COMEX 黄金行情流（T2 收编 C3）'
    """

    def __init__(self, symbol: str = '', **kwargs):
        super().__init__(**kwargs)
        self.symbol = symbol or GOLD_SYMBOL

    def poll_once(self) -> list:
        rows = []
        try:
            rows += self._fetch_ticker()
            rows += self._fetch_candles()
        except Exception as e:
            logger.warning(f'[gold_market] 采集异常: {e}')
        return rows

    def _row(self, data_type: str, payload: dict, ts_ts) -> dict | None:
        import json as _json
        ts = _fmt_ts(ts_ts)
        md5 = __import__('hashlib').md5(f'{self.symbol}|{data_type}|{ts}'.encode()).hexdigest()
        return {
            'symbol': self.symbol,
            'data_type': data_type,
            'payload': _json.dumps(payload, ensure_ascii=False),
            'ts': ts,
            'md5_value': md5,
        }

    def _fetch_ticker(self) -> list:
        """最新快照：取日K CSV 最后一行（stooq /q/l/ 单点端点不可靠）"""
        r = requests.get(_STOOQ_DAILY, params={'s': self.symbol, 'i': 'd'},
                         headers={'User-Agent': _UA}, timeout=10)
        r.raise_for_status()
        lines = [ln.strip() for ln in r.text.strip().splitlines() if ln.strip()]
        if len(lines) < 2:
            return []
        cols = lines[0].split(',')
        vals = lines[-1].split(',')
        row = dict(zip(cols, vals))
        try:
            payload = {
                'last': float(row.get('Close', 0)),
                'open': float(row.get('Open', 0)),
                'high': float(row.get('High', 0)),
                'low': float(row.get('Low', 0)),
                'volume': int(float(row.get('Volume', 0))),
                'date': row.get('Date', ''),
            }
        except (ValueError, TypeError):
            return []
        ts = _date_ts(row.get('Date', '')) or int(time.time() * 1000)
        return [self._row('ticker', payload, ts)]

    def _fetch_candles(self) -> list:
        """日 K CSV：Date,Open,High,Low,Close,Volume（近 N 根追加）"""
        r = requests.get(_STOOQ_DAILY, params={'s': self.symbol, 'i': 'd'},
                         headers={'User-Agent': _UA}, timeout=10)
        r.raise_for_status()
        lines = [ln.strip() for ln in r.text.strip().splitlines() if ln.strip()]
        if len(lines) < 2:
            return []
        cols = lines[0].split(',')
        rows = []
        for ln in lines[1:][-GOLD_CANDLES:]:
            vals = ln.split(',')
            row = dict(zip(cols, vals))
            try:
                payload = {
                    'o': float(row.get('Open', 0)), 'h': float(row.get('High', 0)),
                    'l': float(row.get('Low', 0)), 'c': float(row.get('Close', 0)),
                    'vol': int(float(row.get('Volume', 0))),
                }
            except (ValueError, TypeError):
                continue
            ts = _date_ts(row.get('Date', ''))
            rows.append(self._row('candle', payload, ts))
        return [r for r in rows if r]


def _date_ts(date_str: str) -> int:
    """'YYYY-MM-DD' → 毫秒时间戳（带时区，UTC）"""
    try:
        dt = datetime.strptime(date_str.strip(), '%Y-%m-%d')
        return int(dt.timestamp() * 1000)
    except (ValueError, AttributeError):
        return int(time.time() * 1000)


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
    collector = GoldCollector()
    try:
        collector.start()
    except KeyboardInterrupt:
        logger.info('[gold_market] 收到退出信号')
        collector.stop()


if __name__ == '__main__':
    main()
