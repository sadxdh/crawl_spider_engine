"""宏观价格流采集器（strategy price_fetcher 收编 · 统一采集归爬虫平台）

数据源：腾讯行情（qt.gtimg.cn，经 SOCKS5 11080 代理），覆盖日报所需传统资产：
  - 黄金   hf_GC    纽约黄金期货
  - 现货金 hf_XAU   伦敦金（现货黄金）
  - 原油   hf_CL    纽约原油期货
  - 美股   usDJI/usIXIC/usINX  道琼斯/纳斯达克/标普500
  - A股    sh000300 沪深300
  - BTC    hf_BTC   比特币（腾讯行情，备用；爬虫 market_data 已有 OKX BTC）

网络：腾讯行情在腾讯云服务器直连被重置，必须走 SOCKS5 代理：
  PRICE_SOCKS5_PROXY / ALL_PROXY → 默认 socks5://host.docker.internal:11080
（仅采集器使用代理——符合"只有爬虫会调用代理采集数据"的规则）

数据落点：crawl_data.macro_prices（全量落库 v6.2，INSERT IGNORE 去重）。

运行（独立进程，非 Scrapy）：
  python -m collectors.macro_prices_collector
"""
import json
import os
import time
from datetime import datetime

import requests
from loguru import logger

from collectors.base_collector import BaseCollector

_QT_URL = 'https://qt.gtimg.cn/q='
_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0'}

# 腾讯行情必须走 SOCKS5（直连被重置）
_SOCKS5_PROXY = (os.getenv('PRICE_SOCKS5_PROXY')
                 or os.getenv('ALL_PROXY')
                 or 'socks5://host.docker.internal:11080')
_PROXIES = {'http': _SOCKS5_PROXY, 'https': _SOCKS5_PROXY} if _SOCKS5_PROXY else {}

POLL_INTERVAL = int(os.getenv('MACRO_PRICES_POLL_INTERVAL', '300'))  # 5min

# 腾讯代码 → (ticker, display)（BTC 由爬虫 market_data/OKX 提供，此处不含）
QT_CODES = {
    'hf_GC':  ('XAU', '黄金'),
    'hf_XAU': ('XAU_SPOT', '伦敦金'),
    'hf_CL':  ('WTI', '原油'),
    'usDJI':  ('DJI', '道琼斯'),
    'usIXIC': ('IXIC', '纳斯达克'),
    'usINX':  ('SP500', '标普500'),
    'sh000300': ('CSI300', '沪深300'),
    'whUSDJPY': ('JPY', '日元'),
}


class MacroPricesCollector(BaseCollector):
    """宏观价格流：腾讯行情 → crawl_data.macro_prices"""

    name = 'macro_prices'
    data_table = 'macro_prices'
    poll_interval = POLL_INTERVAL

    table_ddl = """
    CREATE TABLE IF NOT EXISTS `macro_prices` (
      `id` BIGINT NOT NULL AUTO_INCREMENT,
      `ticker` VARCHAR(20) NOT NULL COMMENT 'XAU/WTI/SP500/CSI300/BTC...',
      `display` VARCHAR(40) NOT NULL DEFAULT '' COMMENT '中文名',
      `data_type` VARCHAR(20) NOT NULL DEFAULT 'ticker',
      `payload` TEXT NOT NULL COMMENT '价格 JSON',
      `ts` DATETIME NOT NULL COMMENT '采集时间',
      `md5_value` VARCHAR(64) NOT NULL COMMENT '去重键（ticker|type|ts分钟）',
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_md5` (`md5_value`),
      KEY `ix_ticker_ts` (`ticker`, `ts`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='宏观价格流（腾讯行情，T2 收编 C3）'
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_snapshot = {}

    # ── 腾讯行情 ────────────────────────────────────────────

    @staticmethod
    def _parse_qt_line(line: str) -> dict | None:
        """解析腾讯行情一行，两种格式：
        - 期货/外汇（逗号）：v_hf_GC="价格,涨跌,买价,昨收,最高,最低,时间,..."
          [0]=价格 [1]=涨跌 [2]=买价 [3]=昨收 [4]=最高 [5]=最低
        - 股票/指数（波浪号）：v_usDJI="200~名称~代码~价格~昨收~今开~..."
          [3]=价格 [4]=昨收 [5]=今开 [31]=涨跌 [32]=涨跌% [33]=最高 [34]=最低
        """
        try:
            if '="' not in line:
                return None
            key = line.split('=')[0].strip().replace('v_', '')
            data = line.split('="')[1].rstrip('"')
            if '~' in data:
                f = data.split('~')
                if len(f) < 6:
                    return None
                last = _to_float(f[3])
                if last is None or last == 0:
                    return None
                prev_close = _to_float(f[4]) or last
                high = _to_float(f[33]) if len(f) > 33 and _to_float(f[33]) else last
                low = _to_float(f[34]) if len(f) > 34 and _to_float(f[34]) else last
                chg_pct = _to_float(f[32]) if len(f) > 32 else None
            else:
                f = data.split(',')
                if len(f) < 6:
                    return None
                last = _to_float(f[0])
                if last is None or last == 0:
                    return None
                prev_close = _to_float(f[3]) or last
                high = _to_float(f[4]) or last
                low = _to_float(f[5]) or last
                chg_pct = _to_float(f[1]) if len(f) > 1 else None
            if chg_pct is None:
                chg_pct = round((last / prev_close - 1) * 100, 2) if prev_close else 0
            return {
                'latest': round(last, 4),
                'high_24h': round(high, 4),
                'low_24h': round(low, 4),
                'open_24h': round(prev_close, 4),
                'change_pct': round(chg_pct, 2),
                'asof_ts': int(time.time() * 1000),
                'source': 'tencent',
            }
        except Exception:
            return None

    def _fetch_qt(self, codes: list) -> dict:
        """批量请求腾讯行情，返回 {ticker: parsed}"""
        if not _PROXIES:
            return {}
        results = {}
        try:
            r = requests.get(_QT_URL + ','.join(codes), headers=_HEADERS, timeout=12,
                             proxies=_PROXIES)
            r.encoding = 'gbk'
            for line in r.text.strip().split('\n'):
                parsed = self._parse_qt_line(line)
                if not parsed:
                    continue
                key = line.split('=')[0].strip().replace('v_', '')
                mapping = QT_CODES.get(key)
                if not mapping:
                    continue
                ticker, display = mapping
                parsed['ticker'] = ticker
                parsed['display'] = display
                results[ticker] = parsed
        except Exception as e:
            logger.warning(f'[macro_prices] 腾讯行情请求失败: {e}')
        return results

    # ── BaseCollector 实现 ───────────────────────────────────

    def poll_once(self) -> list:
        results = self._fetch_qt(list(QT_CODES.keys()))
        if not results:
            logger.warning('[macro_prices] 腾讯行情无数据（代理不可用？）')
        rows = []
        now_min = int(time.time() // 60) * 60  # 分钟级去重键
        for ticker, p in results.items():
            payload = json.dumps(p, ensure_ascii=False)
            rows.append({
                'ticker': ticker,
                'display': p.get('display', ticker),
                'data_type': 'ticker',
                'payload': payload,
                'ts': datetime.fromtimestamp(now_min),
                'md5_value': f'{ticker}|ticker|{now_min}',
            })
        logger.info(f'[macro_prices] 腾讯行情: {len(results)} 品种 ({", ".join(sorted(results.keys()))})')
        return rows


def _to_float(v) -> float | None:
    try:
        f = float(v)
        return f
    except (TypeError, ValueError):
        return None


if __name__ == '__main__':
    MacroPricesCollector().start()
