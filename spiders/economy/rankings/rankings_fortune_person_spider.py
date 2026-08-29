"""财富中文网榜单爬虫 → rankings_information"""
import hashlib, scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *
import time

class RankingsFortunePersonSpider(BaseSpider):
    name = 'economy_rankings_fortune_person'
    data_table = 'personal_rankings'
    allowed_domains = ['www.fortunechina.com']
    custom_settings = {'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1}
    proxy_type = 'long_proxy'
    dedup_fields = ['md5_value']
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Referer': 'https://www.fortunechina.com/impact/2021.htm',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Priority': 'u=1',
    }

    def parse_urllist(self, response):
        parser = etree.HTMLParser(encoding='utf-8')
        etree_html = etree.fromstring(response.body, parser=parser)
        url_htmls = etree_html.xpath("/html/body/div[4]/div/div[2]")
        for url_html in url_htmls:
            url_lists = []
            title_lists = []
            url_titles = url_html.xpath("//a[@class='tit']")
            for titles in url_titles:
                title = titles.text
                title_lists.append(title)
                bd_item_inner = titles.xpath('../..')[0]  # 上升到二级父节点
                more_elements = bd_item_inner.xpath('.//a[@class="more"]')
                if more_elements:
                    for more_element in more_elements:
                        more_href = more_element.get('href')
                        url_lists.append(more_href)
                else:
                    url_lists.append('')
        return url_lists, title_lists

    def start_requests(self):
        url = 'https://www.fortunechina.com/rankings/home.htm'
        yield scrapy.Request(
            url=url,
            headers=self.headers,
            callback=self.get_url_list,
            errback=self.errback
        )

    def get_url_list(self, response):
        """获取当前所有榜单的所有年限url"""
        url_lists, title_lists = self.parse_urllist(response)
        url_dicts = {}
        for title, url in zip(title_lists, url_lists):
            if url:  # 检查链接是否为空
                url_dicts[title] = url
        url_dicts = {k: v for k, v in url_dicts.items() if
                     k in ['中国最具影响力的商界女性',  # '全球最具影响力的商界女性', '全球40位40岁以下商界精英',
                           '中国40位40岁以下的商界精英']}

        for url_value in url_dicts.values():
            yield scrapy.Request(
                url=url_value,
                headers=self.headers,
                callback=self.parse_list,
                errback=self.errback,
                dont_filter=True,
                cb_kwargs={'url_dicts': url_dicts, 'url_value': url_value}
            )
    def parse_list(self, response, url_dicts, url_value):
        urls = [v for v in url_dicts.values()]
        etree_html = etree.HTML(response.body)
        # 解析得到所有历史年份的url
        urls_datelist = etree_html.xpath('//div[@class="swiper-wrapper"]')
        for urls_dates in urls_datelist:
            urls_date = urls_dates.xpath('.//a/@href')
            # 网页抓取的链接不完整，需要将相对路径进行拼接转换为绝对路径
            for url in urls_date:
                urls.append(urljoin(url_value, url))
        # 对抓取的url集合去重
        urls_list = list(set(urls))
        for url_urls in urls_list:
            time.sleep(2)
            yield scrapy.Request(
                url=url_urls,
                headers=self.headers,
                callback=self.parse_itme,
                errback=self.errback,
                dont_filter=True,
                cb_kwargs={'url': url_urls}
            )

    def parse_itme(self, response, url):
        """个人榜单解析"""
        etree_html = etree.HTML(response.body)
        title = xpath_parse(etree_html, '//div[@class="inner-page-title"]/text()')
        people_list = xpath_parse(etree_html, '//ul[@class="people-list"]/li[@class="people-item"]',
                                  return_list=True)

        for people in people_list:
            name = people.xpath('.//div[@class="txt"]/div[@class="name"]/text()')[0].strip()
            intro = people.xpath('.//div[@class="txt"]/div[@class="post"]/text()')[0].strip()
            items = {}
            items['rankings_title'] = title
            items['md5_value'] = hash_md5(title + name)
            items['name'] = name
            items['position'] = intro
            yield items



    def errback(self, failure): self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
