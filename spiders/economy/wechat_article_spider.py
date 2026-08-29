"""微信公众号文章 → entity_wechat_article
数据来源：搜狗微信搜索 (weixin.sogou.com)
"""
import hashlib, re, scrapy
from lxml import etree
from datetime import datetime
from spiders.base_spider import BaseSpider

_HDRS = {
    'Accept': 'text/html,application/xhtml+xml,*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36',
}

def _md5(s):
    return hashlib.md5(str(s or '').encode()).hexdigest()


class WechatArticleSpider(BaseSpider):
    """搜狗微信搜索 — 按公众号名称搜索文章"""
    name = 'economy_wechat_article'
    data_table = 'entity_wechat_file_upload'
    dedup_fields = ['announcement_url']
    allowed_domains = ['weixin.sogou.com', 'mp.weixin.qq.com']
    default_end_page = 3

    custom_settings = {
        'CONCURRENT_REQUESTS': 2,
        'DOWNLOAD_DELAY': 2,
    }

    # 默认公众号列表（可通过 -a accounts=xxx 覆盖）
    _DEFAULT_ACCOUNTS = ['人民日报', '新华社', '央视新闻', '国家税务总局', '证监会发布']

    def start_requests(self):
        accounts_str = getattr(self, 'accounts', '')
        accounts = accounts_str.split(',') if accounts_str else self._DEFAULT_ACCOUNTS
        for account in accounts:
            account = account.strip()
            if not account:
                continue
            search_url = f'https://weixin.sogou.com/weixin?type=1&query={account}'
            yield scrapy.Request(url=search_url, headers=_HDRS, callback=self._parse_account,
                                 errback=self.errback, meta={'account': account})

    def _parse_account(self, response):
        tree = etree.HTML(response.body)
        # 获取公众号链接
        for a in tree.xpath('//p[@class="tit"]/a|//div[contains(@class,"img-box")]/a'):
            href = a.get('href', '')
            name = ''.join(a.xpath('.//text()')).strip()
            if '/weixin?type=2&' in href or 'profile' in href:
                yield scrapy.Request(url=response.urljoin(href), headers=_HDRS,
                                     callback=self._parse_article_list,
                                     errback=self.errback,
                                     meta={'account': name or response.meta['account']})

    def _parse_article_list(self, response):
        tree = etree.HTML(response.body)
        account = response.meta['account']

        for li in tree.xpath('//ul[contains(@class,"news-list")]/li|//div[contains(@class,"txt-box")]'):
            title = ''.join(li.xpath('.//h3//text()|.//a[@id]//text()')).strip()
            href = ''
            for a in li.xpath('.//a[@href]'):
                h = a.get('href', '')
                if 'mp.weixin.qq.com' in h or '/link?' in h:
                    href = h
                    break
            date_str = ''.join(li.xpath('.//span[contains(@class,"time")]//text()|.//em[contains(@class,"date")]//text()')).strip()

            if not title or not href:
                continue

            item = {
                'announcement_title': title[:300],
                'announcement_url': response.urljoin(href) if not href.startswith('http') else href,
            }
            yield item

            # 获取文章详情
            detail_url = response.urljoin(href) if not href.startswith('http') else href
            yield scrapy.Request(url=detail_url, headers=_HDRS,
                                 callback=self._parse_detail,
                                 errback=self.errback,
                                 meta={'title': title, 'account': account})

    def _parse_detail(self, response):
        tree = etree.HTML(response.body)
        content = ' '.join(tree.xpath('//div[@id="js_content"]//text()')).strip()
        if not content:
            content = ' '.join(tree.xpath('//div[contains(@class,"rich_media")]//text()')).strip()

        item = {
            'announcement_title': response.meta['title'][:300],
            'announcement_url': response.url,
        }
        yield item

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
