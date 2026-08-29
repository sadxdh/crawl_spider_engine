"""OKX 微观结构采集器（T2 收编 C3 · 情报部 okx_microstructure.py 迁入）

数据源：OKX 公开 REST rubik 统计接口（无需密钥）：
  - /api/v5/rubik/stat/taker-volume    taker 买卖量（ccy/instType/period）
  - /api/v5/rubik/stat/contracts/open-interest-volume  合约持仓量
  - /api/v5/public/funding-rate        资金费率

数据落点：crawl_data.okx_microstructure（全量落库 v6.2）。

运行（独立进程，非 Scrapy）：
  python -m collectors.okx_microstructure_collector
  环境变量：MICRO_CCY=BTC,ETH（默认 BTC）
"""
import os
import time
from datetime import datetime

import requests
from loguru import logger

from collectors.base_collector import BaseCollector, get_proxies

_OKX_BASE = 'https://www.okx.com/api/v5'
_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0'
# 出网：默认直连（NO_PROXY），配置 CRAWL_OUTBOUND_PROXY 时走兜底代理

DEFAULT_CCY = os.getenv('MICRO_CCY', 'BTC').split(',')


class OkxMicrostructureCollector(BaseCollector):
    """OKX 微观指标：taker-volume/oi/funding → crawl_data.okx_microstructure"""

    name = 'okx_microstructure'
    data_table = 'okx_microstructure'
    poll_interval = 300  # 5min 轮询（rubik 统计周期）

    table_ddl = """
    CREATE TABLE IF NOT EXISTS `okx_microstructure` (
      `id` BIGINT NOT NULL AUTO_INCREMENT,
      `ccy` VARCHAR(10) NOT NULL COMMENT '币种：BTC/ETH',
      `data_type` VARCHAR(30) NOT NULL COMMENT 'taker_vol/oi/funding',
      `payload` TEXT NOT NULL COMMENT '统计 JSON',
      `ts` DATETIME NOT NULL COMMENT '统计时间或采集时间',
      `md5_value` VARCHAR(64) NOT NULL COMMENT '去重键（ccy|type|ts）',
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_md5` (`md5_value`),
      KEY `ix_ccy_type` (`ccy`, `data_type`),
      KEY `ix_ts` (`ts`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='OKX 微观结构流（T2 收编 C3）'
    """

    def __init__(self, ccy_list=None, **kwargs):
        super().__init__(**kwargs)
        self.ccy_list = [c.strip().upper() for c in (ccy_list or DEFAULT_CCY) if c.strip()]

    def poll_once(self) -> list:
        rows = []
        for ccy in self.ccy_list:
            try:
                rows += self._fetch_taker_vol(ccy)
                rows += self._fetch_oi(ccy)
                rows += self._fetch_funding(ccy)
            except Exception as e:
                logger.warning(f'[okx_microstructure] {ccy} 异常: {e}')
        return rows

    def _row(self, ccy: str, data_type: str, payload: dict, ts_ts) -> dict | None:
        import json as _json
        ts = _fmt_ts(ts_ts)
        md5 = __import__('hashlib').md5(f'{ccy}|{data_type}|{ts}'.encode()).hexdigest()
        return {
            'ccy': ccy,
            'data_type': data_type,
            'payload': _json.dumps(payload, ensure_ascii=False),
            'ts': ts,
            'md5_value': md5,
        }

    def _get(self, path: str, params: dict) -> dict:
        r = requests.get(f'{_OKX_BASE}{path}', params=params,
                         headers={'User-Agent': _UA}, timeout=10, proxies=get_proxies())
        r.raise_for_status()
        data = r.json()
        if data.get('code') != '0':
            raise RuntimeError(f"OKX error: {data.get('msg')}")
        return data.get('data') or []

    def _fetch_taker_vol(self, ccy: str) -> list:
        data = self._get('/rubik/stat/taker-volume',
                         {'ccy': ccy, 'instType': 'CONTRACTS', 'period': '5m'})
        rows = []
        for d in data:
            # rubik 返回 list-of-list: [ts, sellVol, buyVol]
            if isinstance(d, list) and len(d) >= 3:
                ts_raw = d[0]
                payload = {'ts': d[0], 'sell_vol': d[1], 'buy_vol': d[2]}
            else:
                ts_raw = d.get('ts', int(time.time() * 1000)) if isinstance(d, dict) else int(time.time() * 1000)
                payload = d
            rows.append(self._row(ccy, 'taker_vol', payload, ts_raw))
        return [r for r in rows if r]

    def _fetch_oi(self, ccy: str) -> list:
        data = self._get('/rubik/stat/contracts/open-interest-volume',
                         {'ccy': ccy, 'period': '5m'})
        rows = []
        for d in data:
            if isinstance(d, list) and len(d) >= 3:
                ts_raw = d[0]
                payload = {'ts': d[0], 'oi': d[1], 'vol': d[2]}
            else:
                ts_raw = d.get('ts', int(time.time() * 1000)) if isinstance(d, dict) else int(time.time() * 1000)
                payload = d
            rows.append(self._row(ccy, 'oi', payload, ts_raw))
        return [r for r in rows if r]

    def _fetch_funding(self, ccy: str) -> list:
        inst = f'{ccy}-USDT-SWAP'
        data = self._get('/public/funding-rate', {'instId': inst})
        rows = []
        for d in data:
            ts_raw = d.get('fundingTime', int(time.time() * 1000))
            rows.append(self._row(ccy, 'funding', d, ts_raw))
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
    collector = OkxMicrostructureCollector()
    try:
        collector.start()
    except KeyboardInterrupt:
        logger.info('[okx_microstructure] 收到退出信号')
        collector.stop()


if __name__ == '__main__':
    main()
