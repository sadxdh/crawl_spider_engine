"""App Store榜单 → entity_app_store_rank
App Store RSS Feed: https://rss.applemarketingtools.com/
"""
import hashlib, json, scrapy
from lxml import etree
from spiders.base_spider import BaseSpider

_HDRS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36'}

# App Store RSS feeds for top charts (free/paid/grossing)
_RSS_FEEDS = {
    'ios_free': 'https://rss.marketingtools.apple.com/api/v2/cn/apps/top-free/25/apps.json',
    'ios_paid': 'https://rss.marketingtools.apple.com/api/v2/cn/apps/top-paid/25/apps.json',
    'ios_grossing': 'https://rss.marketingtools.apple.com/api/v2/cn/apps/top-grossing/25/apps.json',
}

def _md5(s):
    return hashlib.md5(str(s or '').encode()).hexdigest()


class AppStoreRankSpider(BaseSpider):
    name = 'economy_app_store_rank'
    data_table = 'rankings_information'
    dedup_fields = ['md5_value']
    allowed_domains = ['rss.marketingtools.apple.com', 'applemarketingtools.com', 'itunes.apple.com']
    default_end_page = 1

    custom_settings = {'CONCURRENT_REQUESTS': 3, 'DOWNLOAD_DELAY': 1}

    def start_requests(self):
        for rank_type, url in _RSS_FEEDS.items():
            yield scrapy.Request(url=url, headers=_HDRS, callback=self._parse,
                                 errback=self.errback, meta={'rank_type': rank_type})

    def _parse(self, response):
        rank_type = response.meta['rank_type']
        try:
            data = response.json()
            entries = data.get('feed', {}).get('results', [])
        except Exception:
            return
        for i, entry in enumerate(entries):
            item = {
                'rankings_name': 'App Store',
                'ranking': i + 1,
                'rankings_type': rank_type,
                'rankings_title': entry.get('name', ''),
                'url': entry.get('url', ''),
                'release_date': entry.get('releaseDate', ''),
                'source': 'App Store',
                'md5_value': _md5(f'{rank_type}_{entry.get("id","")}'),
            }
            yield item

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')


class AppStoreDetailSpider(BaseSpider):
    """App Store应用详情 — 通过iTunes Search API"""
    name = 'economy_app_store_detail'
    data_table = 'app_info'
    dedup_fields = ['md5_value']
    allowed_domains = ['itunes.apple.com']
    default_end_page = 1

    custom_settings = {'CONCURRENT_REQUESTS': 5, 'DOWNLOAD_DELAY': 0.5}

    # 默认查询的热门App ID（可通过 -a app_ids=xxx,yyy 覆盖）
    _DEFAULT_APP_IDS = ['414478124', '444934666', '387682726', '506003812', '333903271']

    def start_requests(self):
        app_ids_str = getattr(self, 'app_ids', '')
        if app_ids_str:
            app_ids = app_ids_str.split(',')
        else:
            app_ids = self._DEFAULT_APP_IDS
        for app_id in app_ids:
            yield scrapy.Request(
                url=f'https://itunes.apple.com/cn/lookup?id={app_id}',
                headers=_HDRS, callback=self._parse,
                errback=self.errback, meta={'app_id': app_id})

    def _parse(self, response):
        try:
            data = response.json()
            results = data.get('results', [])
        except Exception:
            return
        for r in results:
            item = {
                'app_name': r.get('trackName', ''),
                'developer': r.get('artistName', ''),
                'version': r.get('version', ''),
                'average_rating': r.get('averageUserRating', 0),
                'summary': (r.get('description', '') or '')[:2000],
                'apk_size': str(r.get('fileSizeBytes', '')),
                'ios_url': r.get('trackViewUrl', ''),
                'platform': 'ios',
                'md5_value': _md5(str(r.get('trackId', ''))),
            }
            yield item

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
