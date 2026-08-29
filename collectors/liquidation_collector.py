"""清算数据采集器（T2 收编 C3 · 交易部 liquidation.py 迁入）

数据源：
  1. OKX REST /market/trades — 最近成交（公开，含 side 买卖方向，强平单近似）
  2. Coinglass /futures/liquidation_map — 行业清算热力图（需 CG_API_KEY，缺失时跳过）

注：OKX v5 无 history-liquidation REST 端点（强平流走 WS liquidation-orders），
REST 侧以最近成交 + 方向近似；实时强平流后续版本接 WS。

数据落点：crawl_data.liquidation_data（全量落库 v6.2）。

运行（独立进程，非 Scrapy）：
  python -m collectors.liquidation_collector
  环境变量：LIQ_INST_IDS=BTC-USDT-SWAP,ETH-USDT-SWAP；CG_API_KEY=可选
"""
import os
import time
from datetime import datetime

import requests
from loguru import logger

from collectors.base_collector import BaseCollector

_OKX_BASE = 'https://www.okx.com/api/v5'
_CG_BASE = 'https://open-api.coinglass.com/api/pro/v1'
_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0'

DEFAULT_INSTS = os.getenv('LIQ_INST_IDS', 'BTC-USDT-SWAP,ETH-USDT-SWAP').split(',')


class LiquidationCollector(BaseCollector):
    """清算流：OKX 历史强平 + Coinglass 热力图 → crawl_data.liquidation_data"""

    name = 'liquidation_data'
    data_table = 'liquidation_data'
    poll_interval = 60  # 清算 60s 轮询

    table_ddl = """
    CREATE TABLE IF NOT EXISTS `liquidation_data` (
      `id` BIGINT NOT NULL AUTO_INCREMENT,
      `source` VARCHAR(20) NOT NULL COMMENT 'okx/coinglass',
      `inst_id` VARCHAR(30) NOT NULL COMMENT '合约，如 BTC-USDT-SWAP',
      `data_type` VARCHAR(20) NOT NULL COMMENT 'liquidation/liq_map/liq_chart',
      `side` VARCHAR(10) NOT NULL DEFAULT '' COMMENT 'buy/sell（OKX 强平方向）',
      `payload` TEXT NOT NULL COMMENT '清算 JSON',
      `ts` DATETIME NOT NULL COMMENT '清算时间或采集时间',
      `md5_value` VARCHAR(64) NOT NULL COMMENT '去重键（source|inst|type|ts）',
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_md5` (`md5_value`),
      KEY `ix_inst_type` (`inst_id`, `data_type`),
      KEY `ix_ts` (`ts`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='清算数据流（T2 收编 C3）'
    """

    def __init__(self, inst_ids=None, cg_api_key: str = '', **kwargs):
        super().__init__(**kwargs)
        self.inst_ids = [i.strip() for i in (inst_ids or DEFAULT_INSTS) if i.strip()]
        self.cg_api_key = cg_api_key or os.getenv('CG_API_KEY', '')

    def poll_once(self) -> list:
        rows = []
        for inst in self.inst_ids:
            try:
                rows += self._fetch_okx_liq(inst)
            except Exception as e:
                logger.warning(f'[liquidation_data] OKX {inst} 异常: {e}')
        if self.cg_api_key:
            try:
                rows += self._fetch_cg_map()
            except Exception as e:
                logger.warning(f'[liquidation_data] Coinglass 异常: {e}')
        return rows

    def _row(self, source: str, inst: str, data_type: str, payload: dict,
             ts_ts, side: str = '') -> dict | None:
        import json as _json
        ts = _fmt_ts(ts_ts)
        md5 = __import__('hashlib').md5(f'{source}|{inst}|{data_type}|{ts}'.encode()).hexdigest()
        return {
            'source': source,
            'inst_id': inst,
            'data_type': data_type,
            'side': side,
            'payload': _json.dumps(payload, ensure_ascii=False),
            'ts': ts,
            'md5_value': md5,
        }

    def _fetch_okx_liq(self, inst: str) -> list:
        """OKX 最近成交（最近 20 笔，公开，含买卖方向）"""
        r = requests.get(f'{_OKX_BASE}/market/trades',
                         params={'instId': inst, 'limit': '20'},
                         headers={'User-Agent': _UA}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get('code') != '0':
            raise RuntimeError(f"OKX error: {data.get('msg')}")
        rows = []
        for t in (data.get('data') or []):
            ts = t.get('ts', int(time.time() * 1000))
            side = t.get('side', '')  # buy/sell
            rows.append(self._row('okx', inst, 'trades', t, ts, side))
        return [r for r in rows if r]

    def _fetch_cg_map(self) -> list:
        """Coinglass 清算热力图（行业汇总，2h）"""
        headers = {'apiKey': self.cg_api_key, 'Accept': 'application/json'}
        r = requests.get(f'{_CG_BASE}/futures/liquidation_map',
                         params={'range': '2h'}, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        rows = []
        for item in (data.get('data') or []):
            inst = item.get('symbol', '') or 'AGG'
            ts = int(time.time() * 1000)
            rows.append(self._row('coinglass', inst, 'liq_map', item, ts))
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
    collector = LiquidationCollector()
    try:
        collector.start()
    except KeyboardInterrupt:
        logger.info('[liquidation_data] 收到退出信号')
        collector.stop()


if __name__ == '__main__':
    main()
