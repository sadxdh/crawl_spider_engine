"""Hyperliquid L1 数据采集器（T3 收编 C4 · 风控部 hyperliquid_collector/leaderboard 迁入）

数据源：Hyperliquid 公开 REST（无需密钥）：
  - POST /info (type=meta / clearinghouseState)  账户状态/合约元数据
  - GET  https://stats-data.hyperliquid.xyz/Mainnet/leaderboard  TOP 榜

数据落点：crawl_data.hyperliquid_data（全量落库 v6.2）。

运行（独立进程，非 Scrapy）：
  python -m collectors.hyperliquid_collector
  环境变量：HL_ACCOUNTS=地址1,地址2（可选，跟踪特定地址）；HL_TOP_N=20
"""
import json
import os
import time
from datetime import datetime

import requests
from loguru import logger

from collectors.base_collector import BaseCollector

_HL_API = 'https://api.hyperliquid.xyz'
_HL_LEADERBOARD = 'https://stats-data.hyperliquid.xyz/Mainnet/leaderboard'
_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0'

DEFAULT_ACCOUNTS = os.getenv('HL_ACCOUNTS', '').split(',')
HL_TOP_N = int(os.getenv('HL_TOP_N', '20'))


class HyperliquidCollector(BaseCollector):
    """Hyperliquid：meta + leaderboard + 指定地址账户状态 → crawl_data.hyperliquid_data"""

    name = 'hyperliquid_data'
    data_table = 'hyperliquid_data'
    poll_interval = 300  # 5min 轮询

    table_ddl = """
    CREATE TABLE IF NOT EXISTS `hyperliquid_data` (
      `id` BIGINT NOT NULL AUTO_INCREMENT,
      `data_type` VARCHAR(20) NOT NULL COMMENT 'meta/leaderboard/clearinghouse',
      `account` VARCHAR(70) NOT NULL DEFAULT '' COMMENT '地址（leaderboard/账户状态）',
      `payload` TEXT NOT NULL COMMENT '返回 JSON',
      `ts` DATETIME NOT NULL COMMENT '采集时间',
      `md5_value` VARCHAR(64) NOT NULL COMMENT '去重键（type|account|ts）',
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_md5` (`md5_value`),
      KEY `ix_type_account` (`data_type`, `account`),
      KEY `ix_ts` (`ts`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Hyperliquid L1 数据流（T3 收编 C4）'
    """

    def __init__(self, accounts=None, top_n: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.accounts = [a.strip() for a in (accounts or DEFAULT_ACCOUNTS) if a.strip()]
        self.top_n = top_n or HL_TOP_N

    def poll_once(self) -> list:
        rows = []
        try:
            rows += self._fetch_meta()
        except Exception as e:
            logger.warning(f'[hyperliquid_data] meta 异常: {e}')
        try:
            rows += self._fetch_leaderboard()
        except Exception as e:
            logger.warning(f'[hyperliquid_data] leaderboard 异常: {e}')
        for addr in self.accounts:
            try:
                rows += self._fetch_clearinghouse(addr)
            except Exception as e:
                logger.warning(f'[hyperliquid_data] 账户 {addr[:10]}... 异常: {e}')
        return rows

    def _row(self, data_type: str, account: str, payload: dict, ts_ts) -> dict | None:
        ts = _fmt_ts(ts_ts)
        md5 = __import__('hashlib').md5(f'{data_type}|{account}|{ts}'.encode()).hexdigest()
        return {
            'data_type': data_type,
            'account': account,
            'payload': json.dumps(payload, ensure_ascii=False),
            'ts': ts,
            'md5_value': md5,
        }

    def _post_info(self, payload: dict) -> dict:
        r = requests.post(f'{_HL_API}/info', json=payload,
                          headers={'User-Agent': _UA}, timeout=15)
        r.raise_for_status()
        return r.json()

    def _fetch_meta(self) -> list:
        """链上 meta（全部合约/币对，低频）"""
        meta = self._post_info({'type': 'meta'})
        ts = int(time.time() * 1000)
        return [self._row('meta', '', meta, ts)]

    def _fetch_leaderboard(self) -> list:
        """TOP 榜（胜率/PNL 排行）：返回 {leaderboardRows:[...]}"""
        r = requests.get(f'{_HL_LEADERBOARD}?limit={self.top_n}',
                         headers={'User-Agent': _UA}, timeout=15)
        r.raise_for_status()
        data = r.json()
        items = data.get('leaderboardRows', []) if isinstance(data, dict) else (data or [])
        rows = []
        ts = int(time.time() * 1000)
        for item in items[:self.top_n]:
            addr = item.get('ethAddress', '') or item.get('address', '')
            rows.append(self._row('leaderboard', addr, item, ts))
        return [r for r in rows if r]

    def _fetch_clearinghouse(self, address: str) -> list:
        """指定地址账户状态（持仓/保证金）"""
        state = self._post_info({'type': 'clearinghouseState', 'user': address})
        ts = int(time.time() * 1000)
        return [self._row('clearinghouse', address, state, ts)]


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
    collector = HyperliquidCollector()
    try:
        collector.start()
    except KeyboardInterrupt:
        logger.info('[hyperliquid_data] 收到退出信号')
        collector.stop()


if __name__ == '__main__':
    main()
