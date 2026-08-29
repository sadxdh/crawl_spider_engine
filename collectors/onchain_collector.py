"""链上/市场数据流采集器（T3 链上收编 · 风控部 C4 迁入）

数据源（公开端点，无需密钥或可选 key）：
  - Binance klines/ticker   https://api.binance.com/api/v3/klines?symbol={sym}&interval=1m
  - Binance trades          https://api.binance.com/api/v3/trades?symbol={sym}&limit=200
  - Etherscan 区块号        https://api.etherscan.io/api?module=block&action=eth_block_number&apikey={key}
  - Etherscan 链上健康       https://api.etherscan.io/api?module=stats&action=ethsupply&apikey={key}

数据落点：crawl_data.onchain_data（全量落库 v6.2）。风控部消费 `crawl.onchain.event`
（T3 后续）或直读 onchain_data。

运行（独立进程，非 Scrapy）：
  python -m collectors.onchain_collector
  环境变量：ONCHAIN_SYMBOLS=REUSDT,BTCUSDT（默认 REUSDT）；ETHERSCAN_API_KEY=可选
"""
import hashlib
import json
import os
import time
from datetime import datetime

import requests
from loguru import logger

from collectors.base_collector import BaseCollector

_BINANCE = 'https://api.binance.com/api/v3'
_ETHERSCAN = 'https://api.etherscan.io/api'
_UA = 'Mozilla/5.0'

DEFAULT_SYMBOLS = os.getenv('ONCHAIN_SYMBOLS', 'REUSDT,BTCUSDT').split(',')


def _fmt_ms(ts_ms) -> str:
    try:
        ts = int(ts_ms)
        ts = ts / 1000 if ts > 1e12 else ts
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, OSError, TypeError):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _md5(s) -> str:
    return hashlib.md5(str(s).encode('utf-8', errors='ignore')).hexdigest()


class OnchainCollector(BaseCollector):
    """链上/市场数据采集器：Binance 行情 + Etherscan 链上健康 → crawl_data.onchain_data"""

    name = 'onchain_quote'
    data_table = 'onchain_data'
    poll_interval = 120  # 链上数据低频（120s）

    table_ddl = """
    CREATE TABLE IF NOT EXISTS `onchain_data` (
      `id` BIGINT NOT NULL AUTO_INCREMENT,
      `data_type` VARCHAR(20) NOT NULL COMMENT 'klines/trades/ticker/eth_block/eth_supply',
      `symbol` VARCHAR(30) DEFAULT '' COMMENT '交易对，如 REUSDT',
      `chain` VARCHAR(20) DEFAULT '' COMMENT '链，如 ethereum',
      `payload` TEXT NOT NULL COMMENT '数据 JSON',
      `ts` DATETIME NOT NULL COMMENT '数据时间',
      `md5_value` VARCHAR(64) NOT NULL COMMENT '去重键（type|symbol|ts）',
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_md5` (`md5_value`),
      KEY `ix_type_symbol` (`data_type`, `symbol`),
      KEY `ix_ts` (`ts`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='链上/市场数据流（T3 收编）'
    """

    def __init__(self, symbols=None, etherscan_key: str = '', **kwargs):
        super().__init__(**kwargs)
        self.symbols = [s.strip().upper() for s in (symbols or DEFAULT_SYMBOLS) if s.strip()]
        self.etherscan_key = etherscan_key or os.getenv('ETHERSCAN_API_KEY', '')

    def poll_once(self) -> list:
        rows = []
        for sym in self.symbols:
            try:
                rows += self._fetch_binance(sym)
            except Exception as e:
                logger.warning(f'[onchain_quote] {sym} 采集异常: {e}')
        try:
            rows += self._fetch_etherscan()
        except Exception as e:
            logger.warning(f'[onchain_quote] Etherscan 异常: {e}')
        return rows

    # ── Binance ────────────────────────────────────────────────

    def _row(self, data_type, symbol, payload, ts_ms) -> dict:
        ts = _fmt_ms(ts_ms)
        return {
            'data_type': data_type,
            'symbol': symbol,
            'chain': 'binance',
            'payload': json.dumps(payload, ensure_ascii=False),
            'ts': ts,
            'md5_value': _md5(f'{data_type}|{symbol}|{ts}'),
        }

    def _fetch_binance(self, sym) -> list:
        rows = []
        # 1m kline（最近1根）
        r = requests.get(f'{_BINANCE}/klines', params={'symbol': sym, 'interval': '1m', 'limit': 1},
                         headers={'User-Agent': _UA}, timeout=10)
        r.raise_for_status()
        for c in r.json():
            rows.append(self._row('klines', sym,
                                  {'o': c[1], 'h': c[2], 'l': c[3], 'c': c[4], 'v': c[5]}, c[0]))
        # 24h ticker
        r = requests.get(f'{_BINANCE}/ticker/24hr', params={'symbol': sym},
                         headers={'User-Agent': _UA}, timeout=10)
        r.raise_for_status()
        t = r.json()
        rows.append(self._row('ticker', sym,
                              {'last': t.get('lastPrice'), 'high': t.get('highPrice'),
                               'low': t.get('lowPrice'), 'vol': t.get('volume'),
                               'change_pct': t.get('priceChangePercent')}, int(time.time() * 1000)))
        return rows

    # ── Etherscan（链上健康，可选 key） ────────────────────────

    def _fetch_etherscan(self) -> list:
        rows = []
        params = {'apikey': self.etherscan_key}
        # 最新区块号（无需 key 也返回部分数据，无 key 时跳过失败）
        try:
            r = requests.get(_ETHERSCAN, params={**params,
                              'module': 'block', 'action': 'eth_block_number'}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get('status') == '1':
                    rows.append(self._row('eth_block', 'ETH', {'block': data.get('result')},
                                          int(time.time() * 1000)))
        except Exception as e:
            logger.debug(f'[onchain_quote] eth_block 失败: {e}')
        return rows


def main():
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    collector = OnchainCollector()
    try:
        collector.start()
    except KeyboardInterrupt:
        logger.info('[onchain_quote] 收到退出信号')
        collector.stop()


if __name__ == '__main__':
    main()
