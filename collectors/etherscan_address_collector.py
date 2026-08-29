"""Etherscan 地址交易历史采集器（T3 收编 C4 · 风控部 etherscan_client/collector 迁入）

数据源：Etherscan 公开 API（需 ETHERSCAN_API_KEY，从环境变量读取，缺失时跳过）：
  - action=txlist          正常交易（地址进出）
  - action=tokentx         代币（ERC20）转账

数据落点：crawl_data.etherscan_tx（全量落库 v6.2，增量按 block 水位由 bridge 负责）。

运行（独立进程，非 Scrapy）：
  python -m collectors.etherscan_address_collector
  环境变量：ETHERSCAN_API_KEY=必填；ETH_ADDRESSES=地址1,地址2（逗号分隔）
"""
import os
import time
from datetime import datetime

import requests
from loguru import logger

from collectors.base_collector import BaseCollector, get_proxies

_ES_BASE = 'https://api.etherscan.io/v2/api'  # V2：需 chainid 参数（V1 已废弃）
_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0'
# 出网：默认直连（NO_PROXY），配置 CRAWL_OUTBOUND_PROXY 时走兜底代理（如本地 SSRDOG 9567）
_CHAINID = os.getenv('ETH_CHAINID', '1')  # 1=ETH 主网

DEFAULT_ADDRESSES = os.getenv('ETH_ADDRESSES', '').split(',')


class EtherscanAddressCollector(BaseCollector):
    """地址交易历史：txlist + tokentx → crawl_data.etherscan_tx"""

    name = 'etherscan_tx'
    data_table = 'etherscan_tx'
    poll_interval = 120  # 2min 轮询（Etherscan 限频 5 req/s，单地址 2 请求足够）

    table_ddl = """
    CREATE TABLE IF NOT EXISTS `etherscan_tx` (
      `id` BIGINT NOT NULL AUTO_INCREMENT,
      `address` VARCHAR(70) NOT NULL COMMENT '监控地址',
      `data_type` VARCHAR(20) NOT NULL COMMENT 'txlist/tokentx',
      `payload` TEXT NOT NULL COMMENT '交易 JSON',
      `ts` DATETIME NOT NULL COMMENT '交易时间或采集时间',
      `md5_value` VARCHAR(64) NOT NULL COMMENT '去重键（address|type|hash|ts）',
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_md5` (`md5_value`),
      KEY `ix_addr_type` (`address`, `data_type`),
      KEY `ix_ts` (`ts`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Etherscan 地址交易历史（T3 收编 C4）'
    """

    def __init__(self, addresses=None, api_key: str = '', **kwargs):
        super().__init__(**kwargs)
        self.addresses = [a.strip() for a in (addresses or DEFAULT_ADDRESSES) if a.strip()]
        self.api_key = api_key or os.getenv('ETHERSCAN_API_KEY', '')

    def poll_once(self) -> list:
        if not self.api_key:
            logger.warning('[etherscan_tx] 未设置 ETHERSCAN_API_KEY，跳过')
            return []
        rows = []
        for addr in self.addresses:
            try:
                rows += self._fetch_txlist(addr)
                rows += self._fetch_tokentx(addr)
            except Exception as e:
                logger.warning(f'[etherscan_tx] {addr[:12]}... 异常: {e}')
        return rows

    def _call(self, params: dict) -> dict:
        params['apikey'] = self.api_key
        params.setdefault('chainid', _CHAINID)  # V2 必需
        r = requests.get(_ES_BASE, params=params, headers={'User-Agent': _UA},
                         timeout=15, proxies=get_proxies())
        r.raise_for_status()
        data = r.json()
        if data.get('status') != '1':
            raise RuntimeError(f"Etherscan error: {data.get('message')} {data.get('result')}")
        return data.get('result') or []

    def _row(self, address: str, data_type: str, tx: dict) -> dict | None:
        import json as _json
        ts_raw = tx.get('timeStamp') or tx.get('blockTimestamp') or ''
        ts = _fmt_ts(ts_raw)
        h = tx.get('hash', '')
        md5 = __import__('hashlib').md5(f'{address}|{data_type}|{h}|{ts}'.encode()).hexdigest()
        return {
            'address': address,
            'data_type': data_type,
            'payload': _json.dumps(tx, ensure_ascii=False),
            'ts': ts,
            'md5_value': md5,
        }

    def _fetch_txlist(self, address: str) -> list:
        result = self._call({
            'module': 'account', 'action': 'txlist',
            'address': address, 'startblock': 0, 'endblock': 99999999,
            'page': 1, 'offset': 50, 'sort': 'desc',
        })
        return [r for r in (self._row(address, 'txlist', tx) for tx in result) if r]

    def _fetch_tokentx(self, address: str) -> list:
        result = self._call({
            'module': 'account', 'action': 'tokentx',
            'address': address, 'startblock': 0, 'endblock': 99999999,
            'page': 1, 'offset': 50, 'sort': 'desc',
        })
        return [r for r in (self._row(address, 'tokentx', tx) for tx in result) if r]


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
    collector = EtherscanAddressCollector()
    try:
        collector.start()
    except KeyboardInterrupt:
        logger.info('[etherscan_tx] 收到退出信号')
        collector.stop()


if __name__ == '__main__':
    main()
