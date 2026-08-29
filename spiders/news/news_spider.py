"""通用新闻爬虫 → entity_news
参数化：通过 -a 参数指定站点和采集规则，无需配置文件
"""
import hashlib
import re
import scrapy
from datetime import datetime
from lxml import etree

from spiders.base_spider import BaseSpider

_HDRS = {
    'Accept': 'text/html,application/xhtml+xml,*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36',
}

def _md5(s):
    return hashlib.md5(str(s or '').encode()).hexdigest()


class NewsSpider(BaseSpider):
    name = 'news_universal'
    data_table = 'entity_news'
    dedup_fields = ['md5_value']
    default_end_page = 3

    custom_settings = {
        'CONCURRENT_REQUESTS': 8,
        'DOWNLOAD_DELAY': 0.3,
    }

    def __init__(self, site=None, list_url=None, list_type='gne',
                 json_path='', url_field='', url_tpl='', list_sel='',
                 url_pattern='', **kwargs):
        super().__init__(**kwargs)
        self.site_key = site or 'unknown'
        self.list_url = list_url
        self.list_type = list_type
        self.json_path = json_path
        self.url_field = url_field
        self.url_tpl = url_tpl
        self.list_sel = list_sel
        self.url_pattern = url_pattern  # 文章URL正则，如 '-\d+\.html'
        if not list_url:
            self.logger.error('[news] 缺少 list_url 参数')
        else:
            self.logger.info(f'[news] {site} url={list_url[:60]} type={list_type}')

    def start_requests(self):
        if not self.list_url:
            return

        tpl = self.list_url
        for page in range(1, self.end_page + 1):
            url = tpl.format(page=page) if '{page}' in tpl else tpl
            cb = self._parse_json_list if self.list_type == 'json_api' else self._parse_html_list
            yield scrapy.Request(url=url, headers=_HDRS, callback=cb, errback=self.errback)

    def _parse_json_list(self, response):
        try:
            data = response.json()
        except Exception:
            return

        if self.json_path:
            for key in self.json_path.split('.'):
                if isinstance(data, dict):
                    data = data.get(key, [])
                elif isinstance(data, list) and key.isdigit():
                    data = data[int(key)]
        items = data if isinstance(data, list) else []

        for item in items:
            detail_url = item.get(self.url_field, '') if self.url_field else ''
            if detail_url and self.url_tpl:
                detail_url = self.url_tpl.format(id=detail_url)
            if detail_url:
                yield scrapy.Request(url=detail_url, headers=_HDRS, callback=self._parse_detail, errback=self.errback)

    def _parse_html_list(self, response):
        tree = etree.HTML(response.body)
        # 使用 list_sel 限定列表区域，否则限制为常见列表容器
        if self.list_sel:
            scope_els = tree.cssselect(self.list_sel)[:1]
        else:
            # 自动检测常见列表容器（ul/div含多个li/a结构）
            scope_els = tree.cssselect('ul.list,ul.news-list,.news-list,.article-list,.list-news,.item-list')
        scope = scope_els[0] if scope_els else tree

        links = set()
        for a in scope.cssselect('a[href]') if scope_els else tree.xpath('//a[@href]'):
            href = (a.get('href') or '').strip()
            if not href or href.startswith('#') or href.startswith('javascript'):
                continue
            url = response.urljoin(href)
            # URL模式过滤（如 '-\d+\.html' 匹配 article-12345.html）
            if self.url_pattern and not re.search(self.url_pattern, url):
                continue
            # 过滤非文章链接
            skip = ['/login','/register','/user/','/account','/app/','/download',
                    'javascript','mailto:','favicon','.css','.js','.png','.jpg','.gif','.ico']
            if any(p in url.lower() for p in skip):
                continue
            if url in links:
                continue
            # 过滤掉根路径、纯域名、锚点
            path = url.split('?')[0].split('#')[0]
            if path.rstrip('/').count('/') <= 2:  # 太短的路径通常是导航页
                continue
            links.add(url)
            yield scrapy.Request(url=url, headers=_HDRS, callback=self._parse_detail, errback=self.errback)
        sel = self.list_sel or 'auto'
        pat = self.url_pattern or 'none'
        self.logger.info(f'[news] 列表页提取 {len(links)} 个链接 (sel={sel} pattern={pat})')

    def _parse_detail(self, response):
        tree = etree.HTML(response.text)
        result = {'title': '', 'content': '', 'publish_time': '', 'author': ''}

        # Try GNE first
        try:
            from gne import GeneralNewsExtractor
            result = GeneralNewsExtractor().extract(response.text) or result
        except Exception:
            pass

        # Fallback: lxml extraction
        title = result.get('title', '') or ''.join(tree.xpath('//title/text()')).strip()
        content = result.get('content', '')
        if not content:
            # Remove script/style and get all text
            for bad in tree.xpath('//script|//style|//iframe|//nav|//footer|//header'):
                bad.getparent().remove(bad) if bad.getparent() is not None else None
            content = ' '.join(tree.xpath('//body//text()')).strip()
            content = ' '.join(content.split())[:5000]
        else:
            # Clean GNE content
            ct = etree.HTML(content)
            etree.strip_tags(ct, 'script', 'style', 'iframe')
            content = ' '.join(ct.xpath('//body//text()')).strip()
            content = ' '.join(content.split())[:5000]

        # 内容质量检查
        if not title or len(title) < 4:
            return
        if content and len(content) < 100:
            return  # 内容太短，可能是导航页
        # 过滤导航特征明显的内容
        nav_keywords = ['网站首页', '登录注册', '用户名', '密码', '记住密码', '忘记密码']
        if content and any(kw in content[:200] for kw in nav_keywords) and len(content) < 500:
            return

        item = {
            '_table': 'entity_news',
            'title': title[:300] if title else '',
            'url': response.url,
            'content': content or '',
            'release_time': result.get('publish_time') or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'webname': self.site_key,
            'website': response.url.split('/')[2] if '://' in response.url else '',
            'md5_value': _md5(response.url),
        }
        yield item

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
