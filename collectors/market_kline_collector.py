"""市场 K 线采集器（战略部回测收编 · 统一采集归爬虫平台）

数据源（与战略部 signal_backtest 对齐，源不变、采集方改为爬虫平台）：
  - 加密（BTC/ETH/SOL）：Binance API + vultr SOCKS5 代理（与战略部一致）
  - A股/美股指数：新浪行情（quotes.sina / stock.finance.sina）
  - 商品（黄金/原油）：新浪期货日线（战略部 1d 源）

数据落点：crawl_data.kline_data（全量落库，按 symbol|interval|ts 去重）
清洗规则：kline_data → macro_decision.kline_cache（战略部回测读取）

运行（独立进程，非 Scrapy）：
  python -m collectors.market_kline_collector
"""
import json
import os
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from loguru import logger

from collectors.base_collector import BaseCollector

POLL_INTERVAL = int(os.getenv('KLINE_POLL_INTERVAL', '300'))  # 5min

# ── 加密（Binance + vultr 代理，与战略部一致） ──
_BINANCE_HOSTS = ['api.binance.com', 'api1.binance.com', 'api2.binance.com', 'api3.binance.com']
_PROXY_URL = os.getenv('BINANCE_PROXY', 'socks5h://172.17.0.1:11080')
_CRYPTO = [('BTCUSDT', 'BTCUSDT'), ('ETHUSDT', 'ETHUSDT'), ('SOLUSDT', 'SOLUSDT')]

# ── 指数（新浪，与战略部一致） ──
_SINA_INDEX = {
    'sh000688': ('STAR50', 'Asia/Shanghai', 'cn'),
    'sh000001': ('SSE', 'Asia/Shanghai', 'cn'),
    'sh000300': ('CSI300', 'Asia/Shanghai', 'cn'),
    'sz399006': ('CHINEXT', 'Asia/Shanghai', 'cn'),
    'sh000905': ('CSI500', 'Asia/Shanghai', 'cn'),
    '.IXIC': ('NASDAQ', 'America/New_York', 'us'),
    '.INX': ('SP500', 'America/New_York', 'us'),
    '.DJI': ('DOW', 'America/New_York', 'us'),
}
_SINA_CN_URL = 'https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData'
_SINA_US_URL = 'https://stock.finance.sina.com.cn/usstock/api/jsonp.php/var%20_DATA=/US_MinKService.getMinK'

# ── 商品（新浪期货日线，战略部 1d 源） ──
_SINA_COMMODITY = {'XAU': 'XAU', 'GC': 'GC', 'CL': 'CL', 'OIL': 'OIL'}
_SINA_COMMODITY_URL = ('https://stock2.finance.sina.com.cn/futures/api/jsonp.php'
                       '/var%20_S{today}=/GlobalFuturesService.getGlobalFuturesDailyKLine')


class MarketKlineCollector(BaseCollector):
    """市场 K 线（加密+指数+商品）→ crawl_data.kline_data"""

    name = 'market_kline'
    data_table = 'kline_data'
    poll_interval = POLL_INTERVAL

    table_ddl = """
    CREATE TABLE IF NOT EXISTS `kline_data` (
      `id` BIGINT NOT NULL AUTO_INCREMENT,
      `symbol` VARCHAR(20) NOT NULL COMMENT '输出symbol（BTCUSDT/SP500/XAU...）',
      `interval` VARCHAR(6) NOT NULL DEFAULT '1h',
      `ts` BIGINT NOT NULL COMMENT 'K线开盘毫秒时间戳(UTC)',
      `open` DOUBLE NOT NULL,
      `high` DOUBLE NOT NULL,
      `low` DOUBLE NOT NULL,
      `close` DOUBLE NOT NULL,
      `volume` DOUBLE DEFAULT 0,
      `source` VARCHAR(20) DEFAULT '' COMMENT 'binance/sina',
      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_sym_int_ts` (`symbol`, `interval`, `ts`),
      KEY `ix_symbol` (`symbol`, `ts`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='市场K线（战略部回测收编，爬虫统一采集）'
    """

    def _fetch_binance(self, symbol: str) -> list:
        """Binance 1h K线（vultr 代理）"""
        proxy = {'https': _PROXY_URL, 'http': _PROXY_URL}
        params = {'symbol': symbol, 'interval': '1h', 'limit': 300}
        for host in _BINANCE_HOSTS:
            try:
                r = requests.get(f'https://{host}/api/v3/klines', params=params,
                                 proxies=proxy, timeout=20, verify=False)
                r.raise_for_status()
                return [
                    {'ts': int(c[0]), 'open': float(c[1]), 'high': float(c[2]),
                     'low': float(c[3]), 'close': float(c[4]), 'volume': float(c[5])}
                    for c in r.json()
                ]
            except Exception as e:
                logger.warning(f'[kline] Binance {symbol} via {host} 失败: {e}')
        return []

    def _fetch_sina_cn(self, code: str) -> list:
        """新浪 A股指数 1h"""
        try:
            r = requests.get(_SINA_CN_URL,
                             params={'symbol': code, 'scale': '60', 'ma': 'no', 'datalen': '300'},
                             headers={'User-Agent': 'Mozilla/5.0',
                                      'Referer': 'https://finance.sina.com.cn/'},
                             timeout=20)
            r.raise_for_status()
            rows = []
            for d in r.json():
                ts = int(datetime.strptime(d['day'], '%Y-%m-%d %H:%M:%S')
                         .replace(tzinfo=ZoneInfo('Asia/Shanghai'))
                         .astimezone(ZoneInfo('UTC')).timestamp() * 1000)
                rows.append({'ts': ts, 'open': float(d['open']), 'high': float(d['high']),
                             'low': float(d['low']), 'close': float(d['close']),
                             'volume': float(d.get('volume', 0) or 0)})
            return rows
        except Exception as e:
            logger.warning(f'[kline] 新浪A股 {code} 失败: {e}')
            return []

    def _fetch_sina_us(self, code: str) -> list:
        """新浪 美股指数 1h"""
        try:
            r = requests.get(_SINA_US_URL, params={'symbol': code, 'type': '60'},
                             headers={'User-Agent': 'Mozilla/5.0',
                                      'Referer': 'https://finance.sina.com.cn/'},
                             timeout=20)
            r.raise_for_status()
            m = re.search(r'var\s+_DATA=\((\[.*\])\)\s*;?', r.text, re.DOTALL)
            if not m:
                return []
            rows = []
            for d in json.loads(m.group(1)):
                ts_raw = d['d']
                if isinstance(ts_raw, str):
                    # 美东时间字符串 'YYYY-MM-DD HH:MM:SS'
                    ts = int(datetime.strptime(ts_raw, '%Y-%m-%d %H:%M:%S')
                             .replace(tzinfo=ZoneInfo('America/New_York'))
                             .astimezone(ZoneInfo('UTC')).timestamp() * 1000)
                else:
                    ts = int(datetime.fromtimestamp(int(ts_raw))
                             .replace(tzinfo=ZoneInfo('America/New_York'))
                             .astimezone(ZoneInfo('UTC')).timestamp() * 1000)
                rows.append({'ts': ts, 'open': float(d['o']), 'high': float(d['h']),
                             'low': float(d['l']), 'close': float(d['c']),
                             'volume': float(d.get('v', 0) or 0)})
            return rows
        except Exception as e:
            logger.warning(f'[kline] 新浪美股 {code} 失败: {e}')
            return []

    def _fetch_sina_commodity(self, code: str) -> list:
        """新浪期货日线（战略部 1d 源）"""
        try:
            today = datetime.now().strftime('%Y_%m_%d')
            r = requests.get(_SINA_COMMODITY_URL.format(today=today),
                             params={'symbol': code, '_': today, 'source': 'web'},
                             headers={'User-Agent': 'Mozilla/5.0',
                                      'Referer': 'https://finance.sina.com.cn/futuremarket/'},
                             timeout=20)
            r.raise_for_status()
            m = re.search(r'=\((\[.*\])\)\s*;?', r.text, re.DOTALL)
            if not m:
                return []
            rows = []
            for d in json.loads(m.group(1)):
                ts = int(datetime.strptime(d['date'], '%Y-%m-%d')
                         .replace(tzinfo=ZoneInfo('America/New_York'))
                         .astimezone(ZoneInfo('UTC')).timestamp() * 1000)
                rows.append({'ts': ts, 'open': float(d['open']), 'high': float(d['high']),
                             'low': float(d['low']), 'close': float(d['close']),
                             'volume': float(d.get('volume', 0) or 0)})
            return rows
        except Exception as e:
            logger.warning(f'[kline] 新浪商品 {code} 失败: {e}')
            return []

    def poll_once(self) -> list:
        rows = []
        # 1. 加密（Binance 1h）
        for sym, out in _CRYPTO:
            for k in self._fetch_binance(sym):
                rows.append({'symbol': out, 'interval': '1h', **k, 'source': 'binance'})
        # 2. 指数（新浪 1h）
        for code, (out, tz, market) in _SINA_INDEX.items():
            fn = self._fetch_sina_cn if market == 'cn' else self._fetch_sina_us
            for k in fn(code):
                rows.append({'symbol': out, 'interval': '1h', **k, 'source': 'sina'})
        # 3. 商品（新浪日线 1d）
        for code in _SINA_COMMODITY:
            for k in self._fetch_sina_commodity(code):
                rows.append({'symbol': code, 'interval': '1d', **k, 'source': 'sina'})
        if rows:
            from collections import Counter
            cnt = Counter(r['symbol'] for r in rows)
            logger.info(f'[kline] 采集 {len(rows)} 根K线 {dict(cnt)}')
        return rows


if __name__ == '__main__':
    MarketKlineCollector().start()
