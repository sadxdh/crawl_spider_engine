"""情绪/辅助指标流采集器（情报部 data_fetcher 辅助源迁入）

覆盖情报部日报的辅助指标（非价格行情，属情绪/资金流/市值类）：
  - Fear & Greed   alternative.me/fng（恐惧贪婪指数）
  - 加密市值概览    CoinGecko /api/v3/global（总市值 / BTC / ETH 市占率 / 山寨币市值）
  - 加密板块表现    CoinGecko /api/v3/coins/categories（关键板块 24h 涨跌）
  - FedWatch       CME FedWatch 加息概率（可选，依赖代理可达）

数据落点：crawl_data.sentiment_metrics（全量落库 v6.2）。
情报部消费侧：crawl_sentiment_source 适配器（latest 按 metric 查询）。

运行（独立进程，非 Scrapy）：
  python -m collectors.sentiment_collector
"""
import hashlib
import json
import os
import time
from datetime import datetime

import requests
from loguru import logger

from collectors.base_collector import BaseCollector


def _md5(s) -> str:
    return hashlib.md5(str(s).encode('utf-8', errors='ignore')).hexdigest()


def _now_ts() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class SentimentCollector(BaseCollector):
    """情绪/辅助指标采集器 → crawl_data.sentiment_metrics"""

    name = 'sentiment_metrics'
    data_table = 'sentiment_metrics'
    poll_interval = 600  # 情绪指标 10 分钟（日报粒度）

    table_ddl = """
    CREATE TABLE IF NOT EXISTS `sentiment_metrics` (
      `id` BIGINT NOT NULL AUTO_INCREMENT,
      `metric` VARCHAR(30) NOT NULL COMMENT 'fear_greed/mcap_overview/crypto_sectors',
      `payload` TEXT NOT NULL COMMENT '指标 JSON',
      `ts` DATETIME NOT NULL COMMENT '采集时间',
      `md5_value` VARCHAR(64) NOT NULL COMMENT '去重键（metric|ts）',
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_md5` (`md5_value`),
      KEY `ix_metric` (`metric`),
      KEY `ix_ts` (`ts`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='情绪/辅助指标流（情报部迁入）'
    """

    def poll_once(self) -> list:
        rows = []
        try:
            rows += self._fetch_fear_greed()
        except Exception as e:
            logger.warning(f'[sentiment] fear_greed 异常: {e}')
        try:
            rows += self._fetch_mcap_overview()
        except Exception as e:
            logger.warning(f'[sentiment] mcap_overview 异常: {e}')
        try:
            rows += self._fetch_crypto_sectors()
        except Exception as e:
            logger.warning(f'[sentiment] crypto_sectors 异常: {e}')
        return rows

    def _row(self, metric: str, payload: dict) -> dict:
        ts = _now_ts()
        return {
            'metric': metric,
            'payload': json.dumps(payload, ensure_ascii=False),
            'ts': ts,
            'md5_value': _md5(f'{metric}|{ts}'),
        }

    def _fetch_fear_greed(self) -> list:
        """alternative.me 恐惧贪婪指数（当前 + 前一日）"""
        r = requests.get('https://api.alternative.me/fng/?limit=2', timeout=10)
        if r.status_code != 200:
            return []
        data = r.json().get('data') or []
        if not data:
            return []
        cur = data[0]
        prev = data[1] if len(data) > 1 else {}
        try:
            val = int(cur.get('value', 0))
            prev_val = int(prev.get('value', 0)) if prev else 0
        except (ValueError, TypeError):
            val, prev_val = 0, 0
        return [self._row('fear_greed', {
            'value': val,
            'classification': cur.get('value_classification', ''),
            'change': val - prev_val,
            'timestamp': cur.get('timestamp', ''),
        })]

    def _fetch_mcap_overview(self) -> list:
        """CoinGecko global：总市值 + BTC/ETH 市占率 + 山寨币市值"""
        r = requests.get('https://api.coingecko.com/api/v3/global', timeout=10)
        if r.status_code != 200:
            return []
        d = r.json().get('data') or {}
        if not d:
            return []
        total_mcap = d.get('total_market_cap', {}).get('usd', 0) or 0
        btc_dom = d.get('market_cap_percentage', {}).get('btc', 0) or 0
        eth_dom = d.get('market_cap_percentage', {}).get('eth', 0) or 0
        alt_mcap = total_mcap * (100 - btc_dom) / 100
        return [self._row('mcap_overview', {
            'total_mcap_usd': round(total_mcap, 2),
            'btc_dominance': round(btc_dom, 2),
            'eth_dominance': round(eth_dom, 2),
            'altcoin_mcap_usd': round(alt_mcap, 2),
        })]

    def _fetch_crypto_sectors(self) -> list:
        """CoinGecko categories：关键板块 24h 涨跌"""
        key_sectors = {
            'Layer 1 (L1)', 'Layer 2 (L2)', 'DeFi', 'Meme', 'AI Agents',
            'Solana Ecosystem', 'Ethereum Ecosystem', 'Gaming', 'RWA', 'Stablecoins',
        }
        r = requests.get('https://api.coingecko.com/api/v3/coins/categories', timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        if not isinstance(data, list):
            return []
        captured = {}
        for cat in data[:30]:
            name = cat.get('name', '')
            if name in key_sectors:
                captured[name] = round(cat.get('market_cap_change_24h', 0) or 0, 2)
        # 补漏（key_sectors 中未在前 30 捕获的）
        if len(captured) < len(key_sectors):
            for cat in data:
                name = cat.get('name', '')
                if name in key_sectors and name not in captured:
                    captured[name] = round(cat.get('market_cap_change_24h', 0) or 0, 2)
        return [self._row('crypto_sectors', {'sectors_24h': captured})]


def main():
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    collector = SentimentCollector()
    try:
        collector.start()
    except KeyboardInterrupt:
        logger.info('[sentiment] 收到退出信号')
        collector.stop()


if __name__ == '__main__':
    main()

