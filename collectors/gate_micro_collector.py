"""Gate 合约微观行情流采集器（情报部 market_maker_collector 采集部分迁入）

数据源：Gate.io USDT 永续合约（api.gateio.ws/api/v4/futures/usdt）：
  - tickers      GET /tickers 全合约行情
  - order_book   GET /order_book?contract=BTC_USDT&limit=20
  - funding_rate GET /funding_rate?contract=BTC_USDT
  - contracts    GET /contracts（合约元数据）

数据落点：crawl_data.gate_micro（全量落库 v6.2）。
情报部消费侧：Gamma/清算驱动等本地计算保留情报部（分析职责），
  从 crawl_data 读取微观数据（T2 同构适配器）。

运行（独立进程，非 Scrapy）：
  python -m collectors.gate_micro_collector
"""
import hashlib
import json
import os
import time
from datetime import datetime

import requests
from loguru import logger

from collectors.base_collector import BaseCollector

_GATE = 'https://api.gateio.ws/api/v4/futures/usdt'


def _md5(s) -> str:
    return hashlib.md5(str(s).encode('utf-8', errors='ignore')).hexdigest()


def _now_ts() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class GateMicroCollector(BaseCollector):
    """Gate 合约微观行情采集器 → crawl_data.gate_micro"""

    name = 'gate_micro'
    data_table = 'gate_micro'
    poll_interval = 60  # 微观行情 60s

    table_ddl = """
    CREATE TABLE IF NOT EXISTS `gate_micro` (
      `id` BIGINT NOT NULL AUTO_INCREMENT,
      `data_type` VARCHAR(20) NOT NULL COMMENT 'tickers/order_book/funding_rate/contracts',
      `contract` VARCHAR(30) NOT NULL COMMENT '合约，如 BTC_USDT',
      `payload` TEXT NOT NULL COMMENT '行情 JSON',
      `ts` DATETIME NOT NULL COMMENT '采集时间',
      `md5_value` VARCHAR(64) NOT NULL COMMENT '去重键（type|contract|ts）',
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_md5` (`md5_value`),
      KEY `ix_type_contract` (`data_type`, `contract`),
      KEY `ix_ts` (`ts`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Gate 合约微观行情（情报部迁入）'
    """

    def __init__(self, contracts=None, **kwargs):
        super().__init__(**kwargs)
        self.contracts = [c.strip() for c in
                          (contracts or os.getenv('GATE_CONTRACTS', 'BTC_USDT,ETH_USDT').split(','))
                          if c.strip()]

    def poll_once(self) -> list:
        rows = []
        try:
            rows += self._fetch_tickers()
        except Exception as e:
            logger.warning(f'[gate_micro] tickers 异常: {e}')
        for contract in self.contracts:
            try:
                rows += self._fetch_contract_detail(contract)
            except Exception as e:
                logger.warning(f'[gate_micro] {contract} 异常: {e}')
        return rows

    def _row(self, data_type: str, contract: str, payload: dict) -> dict:
        ts = _now_ts()
        return {
            'data_type': data_type,
            'contract': contract,
            'payload': json.dumps(payload, ensure_ascii=False),
            'ts': ts,
            'md5_value': _md5(f'{data_type}|{contract}|{ts}'),
        }

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        r = requests.get(f'{_GATE}{path}', params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def _fetch_tickers(self) -> list:
        """全合约 tickers（BTC_USDT 等，含 mark_price/index_price/funding_rate）"""
        data = self._get('/tickers')
        rows = []
        if not isinstance(data, list):
            return rows
        for t in data:
            contract = t.get('contract', '')
            if contract in self.contracts:
                rows.append(self._row('tickers', contract, t))
        return rows

    def _fetch_contract_detail(self, contract: str) -> list:
        """order_book + funding_rate + contracts（单合约微观）"""
        rows = []
        try:
            ob = self._get('/order_book', {'contract': contract, 'limit': '20'})
            rows.append(self._row('order_book', contract, ob))
        except Exception as e:
            logger.debug(f'[gate_micro] {contract} order_book: {e}')
        try:
            fr = self._get('/funding_rate', {'contract': contract})
            rows.append(self._row('funding_rate', contract, fr if isinstance(fr, dict) else {}))
        except Exception as e:
            logger.debug(f'[gate_micro] {contract} funding_rate: {e}')
        return rows


def main():
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    collector = GateMicroCollector()
    try:
        collector.start()
    except KeyboardInterrupt:
        logger.info('[gate_micro] 收到退出信号')
        collector.stop()


if __name__ == '__main__':
    main()
