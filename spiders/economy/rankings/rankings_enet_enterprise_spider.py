"""企业网榜单爬虫 → rankings_information"""
import hashlib, scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *
import time

class RankingsEnetEnterpriseSpider(BaseSpider):
    name = 'economy_rankings_enet_enterprise'
    data_table = 'rankings_information'
    allowed_domains = ['enet.com.cn']
    custom_settings = {'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1}
    proxy_type = 'long_proxy'
    dedup_fields = ['md5_value']
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Referer': 'http://enet.com.cn/tag/ranklist?page=90',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            if page == 1:
                url = f'http://enet.com.cn/tag/ranklist?page=1'
            else:
                url = f'http://enet.com.cn/tag/ranklist?page={page}'
            yield scrapy.Request(
                url=url,
                headers=self.headers,
                callback=self.parse_list,
                errback=self.errback
            )

    def parse_list(self, response):
        etree_xpath = etree.HTML(response.body)
        # urls_list = xpath_parse(response.content, '//div[@class="conart"]//li')
        urls_list = etree_xpath.xpath('//div[@class="conart"]//li')
        for urls in urls_list:
            url = urljoin(response.url, urls.xpath('./a/@href')[0])
            release_date = urls.xpath('./span/text()')[0].strip()
            title = urls.xpath('./a/text()')[0].strip()
            temp = {'title': title, 'release_date': release_date, 'entity_url': url}
            yield scrapy.Request(
                url=url,
                headers=self.headers,
                callback=self.parse_detail,
                errback=self.errback,
                cb_kwargs={'parms': temp}
            )

    def parse_detail(self, response, parms):
        title = parms['title'].lstrip('\ufeff')
        release_date = parms['release_date'].strip()
        etree_xpath = etree.HTML(response.body)
        time.sleep(1)
        info = etree_xpath.xpath('//table[@class="rankList_tb"]')
        if info:
            for td in info:
                title2 = td.xpath('./caption/text()')[0].strip() if td.xpath('./caption/text()') else None
                urls_list = td.xpath('.//tbody/tr')
                for tr in urls_list:
                    ranking = tr.xpath('./td[1]/text()')[0].strip() if tr.xpath('./td[1]/text()') else None
                    name = tr.xpath('./td[2]/text()')
                    if not name:
                        name = tr.xpath('./td[2]/a/text()')
                    name = name[0].strip() if name else None
                    if title2 and str(title2) != str(title):
                        title3 = f'{title}-{title2}'
                    else:
                        title3 = title
                    if name and not any(keyword in title3.lower() for keyword in
                                        ["app", "游戏", "公众号", "ip", "小程序", "营销案例", "手游", "电子竞技",
                                         "智能终端", "网红排行榜", "创业者", "画家", "燃油车", "智能手机top",
                                         "推荐图书", "网络大电影", "电竞赛事", "穿戴", "车型", "专家", "产品", "体系",
                                         "景区", "黑科技", "车载配件", "智能音箱", "智能手表", "企业家",
                                         "生活习惯", "表情包", "直播", "电台", "音乐", "动漫", "阅读", "视频", "方案",
                                         "二手",
                                         "付费"]):
                        md5_value = hash_md5(ranking + title3 + name)
                        items = {}
                        items['md5_value'] = md5_value
                        items['url'] = response.url
                        items['ranking'] = ranking
                        items['rankings_title'] = title3
                        items['rankings_name'] = name
                        items['release_date'] = release_date
                        items['source'] = 'eNet硅谷动力'
                        yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
