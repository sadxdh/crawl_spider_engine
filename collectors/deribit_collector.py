"""Deribit 期权微观采集器（T2 收编 C3 · 交易部 gex.py/gamma_exposure.py 迁入）

数据源：Deribit 公开 REST API（无需密钥）：
  - get_book_summary_by_currency  期权汇总（IV/Delta/Gamma/Vega/Theta/标记价）
  - get_instruments                期权合约表
  - ticker                        单合约实时（含 greeks）

数据落点：crawl_data.deribit_options（全量落库 v6.2；快照按 ts 追加）。
GEX/Gamma 聚合分析由消费端（交易部 gamma_exposure）基于本表计算。

运行（独立进程，非 Scrapy）：
  python -m collectors.deribit_collector
  环境变量：DERIBIT_CURRENCIES=BTC,ETH（默认 BTC,ETH）
"""
import os
import time
from datetime import datetime

import requests
from loguru import logger

from collectors.base_collector import BaseCollector

_DERIBIT_BASE = 'https://www.deribit.com/api/v2/public'
_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0'

DEFAULT_CURRENCIES = os.getenv('DERIBIT_CURRENCIES', 'BTC,ETH').split(',')


def _get(path: str, params: dict) -> dict:
    """Deribit 公开 API 用 GET query（官方支持，免认证）"""
    r = requests.get(f'{_DERIBIT_BASE}/{path}', params=params,
                     headers={'User-Agent': _UA}, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data.get('error'):
        raise RuntimeError(f"Deribit error: {data['error']}")
    return data.get('result', {})


class DeribitCollector(BaseCollector):
    """Deribit 期权汇总/greeks → crawl_data.deribit_options"""

    name = 'deribit_options'
    data_table = 'deribit_options'
    poll_interval = 300  # 期权快照 5min 轮询（greeks 变化平缓）

    table_ddl = """
    CREATE TABLE IF NOT EXISTS `deribit_options` (
      `id` BIGINT NOT NULL AUTO_INCREMENT,
      `currency` VARCHAR(10) NOT NULL COMMENT '币种：BTC/ETH',
      `instrument` VARCHAR(50) NOT NULL COMMENT '合约名',
      `data_type` VARCHAR(20) NOT NULL COMMENT 'book_summary/instrument/ticker',
      `payload` TEXT NOT NULL COMMENT 'Deribit 返回 JSON',
      `ts` DATETIME NOT NULL COMMENT '采集时间',
      `md5_value` VARCHAR(64) NOT NULL COMMENT '去重键（instrument|type|ts）',
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_md5` (`md5_value`),
      KEY `ix_inst_type` (`instrument`, `data_type`),
      KEY `ix_ts` (`ts`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Deribit 期权微观流（T2 收编 C3）'
    """

    def __init__(self, currencies=None, **kwargs):
        super().__init__(**kwargs)
        self.currencies = [c.strip().upper() for c in (currencies or DEFAULT_CURRENCIES) if c.strip()]

    def poll_once(self) -> list:
        rows = []
        for cur in self.currencies:
            try:
                rows += self._fetch_book_summary(cur)
                rows += self._fetch_instruments(cur)
            except Exception as e:
                logger.warning(f'[deribit_options] {cur} 采集异常: {e}')
        return rows

    def _row(self, currency: str, instrument: str, data_type: str,
             payload: dict, ts_ts) -> dict | None:
        import json as _json
        ts = _fmt_ts(ts_ts)
        md5 = __import__('hashlib').md5(f'{instrument}|{data_type}|{ts}'.encode()).hexdigest()
        return {
            'currency': currency,
            'instrument': instrument,
            'data_type': data_type,
            'payload': _json.dumps(payload, ensure_ascii=False),
            'ts': ts,
            'md5_value': md5,
        }

    def _fetch_book_summary(self, currency: str) -> list:
        """get_book_summary_by_currency：全部期权合约汇总（含 greeks/IV）"""
        result = _get('get_book_summary_by_currency',
                      {'currency': currency, 'kind': 'option'})
        rows = []
        for s in (result or []):
            inst = s.get('instrument_name', '')
            ts = s.get('timestamp', int(time.time() * 1000))
            rows.append(self._row(currency, inst, 'book_summary', s, ts))
        return [r for r in rows if r]

    def _fetch_instruments(self, currency: str) -> list:
        """get_instruments：合约表（strike/expiry/tick）低频落库"""
        result = _get('get_instruments',
                      {'currency': currency, 'kind': 'option', 'expired': 'false'})
        rows = []
        now = int(time.time() * 1000)
        for i in (result or []):
            inst = i.get('instrument_name', '')
            rows.append(self._row(currency, inst, 'instrument', i, now))
        return [r for r in rows if r]


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
    collector = DeribitCollector()
    try:
        collector.start()
    except KeyboardInterrupt:
        logger.info('[deribit_options] 收到退出信号')
        collector.stop()


if __name__ == '__main__':
    main()
