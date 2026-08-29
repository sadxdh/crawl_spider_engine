"""宏观行情流采集器（情报部 data_fetcher.py 行情迁入 · 日报数据源）

覆盖情报部日报所需的宏观行情（Sina Finance 为主，中国服务器友好）：
  - A股指数    s_sh000001,s_sz399001,s_sh000300,s_sz399006,s_sh000688,s_sh000016
  - 美股指数    int_dji,int_nasdaq,int_sp500
  - 黄金        hf_XAU,hf_GC
  - 原油        hf_CL,hf_OIL
  - 日元/人民币  fx_susdjpy,fx_susdcny
  - 加密 BTC    hf_BTC

Sina 返回 GBK 编码文本，需手动解码（与 data_fetcher.py 一致）。

数据落点：crawl_data.macro_market（全量落库 v6.2）。
情报部消费侧：crawl_macro_source 适配器（T2 同构，见 departments/intelligence）。

运行（独立进程，非 Scrapy）：
  python -m collectors.macro_market_collector
"""
import json
import os
import re
import time
from datetime import datetime

import requests
from loguru import logger

from collectors.base_collector import BaseCollector

_SINA = 'https://hq.sinajs.cn/list='
_HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; GlobalScout/1.0)',
            'Referer': 'https://finance.sina.com.cn/'}

# 品种 → Sina 代码（与 data_fetcher.SINA_CODES 一致）
SINA_CODES = {
    'a_stock':  's_sh000001,s_sz399001,s_sh000300,s_sz399006,s_sh000688,s_sh000016',
    'us_stock': 'int_dji,int_nasdaq,int_sp500',
    'gold':     'hf_XAU,hf_GC',
    'oil':      'hf_CL,hf_OIL',
    'jpy':      'fx_susdjpy',
    'rmb_bond': 'fx_susdcny',
    'crypto':   'hf_BTC',
}


class MacroMarketCollector(BaseCollector):
    """宏观行情采集器：Sina 多品种 → crawl_data.macro_market"""

    name = 'macro_market'
    data_table = 'macro_market'
    poll_interval = 300  # 宏观行情 5 分钟（日报粒度，足够）

    table_ddl = """
    CREATE TABLE IF NOT EXISTS `macro_market` (
      `id` BIGINT NOT NULL AUTO_INCREMENT,
      `product` VARCHAR(20) NOT NULL COMMENT '品种：a_stock/us_stock/gold/oil/jpy/rmb_bond/crypto',
      `code` VARCHAR(30) NOT NULL COMMENT 'Sina 代码，如 s_sh000001',
      `name` VARCHAR(50) DEFAULT '' COMMENT '名称',
      `payload` TEXT NOT NULL COMMENT '行情 JSON',
      `ts` DATETIME NOT NULL COMMENT '采集时间',
      `md5_value` VARCHAR(64) NOT NULL COMMENT '去重键（product|code|ts）',
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_md5` (`md5_value`),
      KEY `ix_product` (`product`),
      KEY `ix_ts` (`ts`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='宏观行情流（情报部日报数据源迁入）'
    """

    def __init__(self, codes: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.codes = codes or SINA_CODES

    def poll_once(self) -> list:
        """单轮：拉全部品种的 Sina 行情 → 构造 macro_market 行"""
        rows = []
        for product, code_str in self.codes.items():
            try:
                rows += self._fetch_product(product, code_str)
            except Exception as e:
                logger.warning(f'[macro_market] {product} 采集异常: {e}')
        return rows

    # ── Sina 解析 ─────────────────────────────────────────────

    def _fetch_product(self, product: str, code_str: str) -> list:
        url = _SINA + code_str
        r = requests.get(url, headers=_HEADERS, timeout=10)
        if r.status_code != 200:
            return []
        # Sina 返回 GBK 编码
        text = r.content.decode('gbk', errors='replace')
        rows = []
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for line in text.strip().splitlines():
            # 格式: var hq_str_s_sh000001="上证指数,3150.12,...";
            m = re.match(r'var hq_str_(\w+)="(.*)";', line)
            if not m:
                continue
            code, raw = m.group(1), m.group(2)
            fields = raw.split(',')
            if not fields or not fields[0]:
                continue
            payload = {'name': fields[0], 'fields': fields[1:], 'raw': raw}
            md5 = __import__('hashlib').md5(
                f'{product}|{code}|{ts}'.encode()).hexdigest()
            rows.append({
                'product': product, 'code': code,
                'name': fields[0][:50], 'payload': json.dumps(payload, ensure_ascii=False),
                'ts': ts, 'md5_value': md5,
            })
        return rows


def main():
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    collector = MacroMarketCollector()
    try:
        collector.start()
    except KeyboardInterrupt:
        logger.info('[macro_market] 收到退出信号')
        collector.stop()


if __name__ == '__main__':
    main()
