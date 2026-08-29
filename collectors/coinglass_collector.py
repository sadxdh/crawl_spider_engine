"""Coinglass 行业数据采集器（T2 收编 C3 · 交易部 liquidation.py 的 Coinglass 部分迁入）

数据源：Coinglass 公开 API（需 CG_API_KEY，从环境变量读取，缺失时跳过）：
  - /futures/liquidation_map      清算热力图（行业汇总）
  - /futures/liquidation_chart    清算图表（多头/空头）
  - /futures/openInterest/...     持仓量（可选，需权限）

数据落点：crawl_data.coinglass_data（全量落库 v6.2）。

运行（独立进程，非 Scrapy）：
  python -m collectors.coinglass_collector
  环境变量：CG_API_KEY=必填；CG_SYMBOLS=BTC,ETH（默认 BTC）
"""
import os
import time
from datetime import datetime

import requests
from loguru import logger

from collectors.base_collector import BaseCollector, get_proxies

_CG_BASE = 'https://open-api.coinglass.com/api/pro/v1'
_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0'
# 出网：默认直连（NO_PROXY），配置 CRAWL_OUTBOUND_PROXY 时走兜底代理

DEFAULT_SYMBOLS = os.getenv('CG_SYMBOLS', 'BTC').split(',')


class CoinglassCollector(BaseCollector):
    """Coinglass 清算/持仓 → crawl_data.coinglass_data"""

    name = 'coinglass_data'
    data_table = 'coinglass_data'
    poll_interval = 300  # 5min 轮询

    table_ddl = """
    CREATE TABLE IF NOT EXISTS `coinglass_data` (
      `id` BIGINT NOT NULL AUTO_INCREMENT,
      `symbol` VARCHAR(20) NOT NULL DEFAULT '' COMMENT '币种：BTC/ETH/AGG',
      `data_type` VARCHAR(30) NOT NULL COMMENT 'liq_map/liq_chart',
      `payload` TEXT NOT NULL COMMENT 'Coinglass 返回 JSON',
      `ts` DATETIME NOT NULL COMMENT '采集时间',
      `md5_value` VARCHAR(64) NOT NULL COMMENT '去重键（symbol|type|ts）',
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_md5` (`md5_value`),
      KEY `ix_sym_type` (`symbol`, `data_type`),
      KEY `ix_ts` (`ts`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Coinglass 行业数据流（T2 收编 C3）'
    """

    def __init__(self, symbols=None, api_key: str = '', **kwargs):
        super().__init__(**kwargs)
        self.symbols = [s.strip().upper() for s in (symbols or DEFAULT_SYMBOLS) if s.strip()]
        self.api_key = api_key or os.getenv('CG_API_KEY', '')

    def poll_once(self) -> list:
        if not self.api_key:
            logger.warning('[coinglass_data] 未设置 CG_API_KEY，跳过')
            return []
        rows = []
        try:
            rows += self._fetch_liq_map()
        except Exception as e:
            logger.warning(f'[coinglass_data] liquidation_map 异常（端点可能无权限）: {e}')
        for sym in self.symbols:
            try:
                rows += self._fetch_liq_chart(sym)
            except Exception as e:
                logger.warning(f'[coinglass_data] {sym} chart 异常（端点可能无权限）: {e}')
        if not rows:
            logger.warning('[coinglass_data] 当前 CG_API_KEY 对 pro 端点无权限（500），数据源不可用，'
                           '请更换有权限的 key 或使用 OKX 清算替代')
        return rows

    def _row(self, symbol: str, data_type: str, payload: dict) -> dict | None:
        import json as _json
        ts = int(time.time() * 1000)
        md5 = __import__('hashlib').md5(f'{symbol}|{data_type}|{ts}'.encode()).hexdigest()
        return {
            'symbol': symbol,
            'data_type': data_type,
            'payload': _json.dumps(payload, ensure_ascii=False),
            'ts': _fmt_ts(ts),
            'md5_value': md5,
        }

    def _headers(self) -> dict:
        return {'apiKey': self.api_key, 'Accept': 'application/json', 'User-Agent': _UA}

    def _fetch_liq_map(self) -> list:
        """清算热力图（2h 行业汇总）"""
        r = requests.get(f'{_CG_BASE}/futures/liquidation_map',
                         params={'range': '2h'}, headers=self._headers(),
                         timeout=10, proxies=get_proxies())
        r.raise_for_status()
        data = r.json()
        if data.get('code') != '0':
            raise RuntimeError(f"Coinglass error: {data.get('msg')}")
        rows = []
        for item in (data.get('data') or []):
            sym = item.get('symbol', '') or 'AGG'
            rows.append(self._row(sym, 'liq_map', item))
        return [r for r in rows if r]

    def _fetch_liq_chart(self, symbol: str) -> list:
        """清算图表（多空方向）"""
        r = requests.get(f'{_CG_BASE}/futures/liquidation_chart',
                         params={'symbol': symbol, 'timeType': 'h', 'type': 'ALL'},
                         headers=self._headers(), timeout=10, proxies=get_proxies())
        r.raise_for_status()
        data = r.json()
        if data.get('code') != '0':
            raise RuntimeError(f"Coinglass error: {data.get('msg')}")
        return [self._row(symbol, 'liq_chart', data.get('data') or {})]


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
    collector = CoinglassCollector()
    try:
        collector.start()
    except KeyboardInterrupt:
        logger.info('[coinglass_data] 收到退出信号')
        collector.stop()


if __name__ == '__main__':
    main()
