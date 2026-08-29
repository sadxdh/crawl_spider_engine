"""新浪财经快讯批模式爬虫（scrapy，按用户要求新浪改批模式爬虫）

数据源：新浪财经快讯滚动接口（feed.mix.sina.com.cn，走 SOCKS5 11080 代理）
  - 快讯列表：https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num=20&page={page}
  - 覆盖：财经快讯（宏观/市场/公司等）

数据落点：crawl_data.news_sina（MysqlPipeline 自动建表 + md5_value 去重）

运行（Scrapyd 批模式调度）：
  scrapy crawl sina_finance -a start_page=1 -a end_page=2
"""
import hashlib

import scrapy

from spiders.base_spider import BaseSpider

_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       'Chrome/130.0.0.0 Safari/537.36')

_API = 'https://feed.mix.sina.com.cn/api/roll/get'
_LID = '2516'  # 财经快讯分类


class SinaFinanceSpider(BaseSpider):
    """新浪财经快讯批模式爬虫"""

    name = 'sina_finance'
    default_start_page = 1
    default_end_page = 5
    data_table = 'news_sina'
    dedup_fields = ['md5_value']
    proxy_type = 'tunnel_proxy'  # 腾讯云直连新浪不可达，走 11080 SOCKS5

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            url = f'{_API}?pageid=153&lid={_LID}&k=&num=20&page={page}'
            yield scrapy.Request(
                url,
                headers={'User-Agent': _UA, 'Referer': 'https://finance.sina.com.cn/'},
                callback=self.parse_page,
                meta={'page': page},
                dont_filter=True,
            )

    def parse_page(self, response):
        data = response.json()
        result = data.get('result', {})
        items = result.get('data', []) or []
        for item in items:
            row = self._to_row(item)
            if row:
                yield row

    def _to_row(self, item: dict) -> dict | None:
        """构造入库行：news_id/md5 去重 + 文本/来源/时间"""
        try:
            news_id = str(item.get('id') or item.get('docid') or '')
            title = (item.get('title') or '').strip()
            intro = (item.get('intro') or '').strip()
            ctime = item.get('ctime') or item.get('create_time') or ''
            url = item.get('url') or item.get('wapurl') or ''
            if not news_id or not title:
                return None
            text = title
            if intro:
                text = f'{title}。{intro}'
            md5 = hashlib.md5(news_id.encode()).hexdigest()
            return {
                'news_id': news_id,
                'text': text,
                'source': 'sina',
                'tag': item.get('tag') or 'finance',
                'docurl': url,
                'news_time': ctime,
                'md5_value': md5,
            }
        except Exception as e:
            self.log_warning(f'行解析失败: {e}')
            return None
