"""创业邦榜单爬虫 → rankings_information"""
import hashlib, scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *

class RankingsCyzonePersonSpider(BaseSpider):
    name = 'economy_rankings_cyzone_person'
    data_table = 'personal_rankings'
    allowed_domains = ['www.cyzone.cn']
    custom_settings = {'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1}
    proxy_type = 'long_proxy'
    dedup_fields = ['md5_value']
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Referer': 'https://www.cyzone.cn/lightlist?share=amountEventList',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Priority': 'u=0, i',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }

    def get_title_url(self):
        title_url = {
            '2021年度投资人': 'https://www.cyzone.cn/billboard/detail/169',
            '2021年40位40岁以下投资人榜单': 'https://www.cyzone.cn/billboard/detail/163',
            '2021年30位30岁以下创业新贵': 'https://www.cyzone.cn/billboard/detail/162',
            '2021最值得关注的女性创业者': 'https://www.cyzone.cn/billboard/detail/158',
            '2021中国女性投资人榜单': 'https://www.cyzone.cn/billboard/child/7799020',
            '2020年度天使投资人': 'https://www.cyzone.cn/billboard/detail/155',
            '2020年度投资人': 'https://www.cyzone.cn/billboard/detail/154',
            '2020年度创业者': 'https://www.cyzone.cn/billboard/detail/153',
            '2020向光奖·年度影响力投资人TOP3': 'https://www.cyzone.cn/billboard/detail/128',
            '2020年40位40岁以下投资人': 'https://www.cyzone.cn/billboard/detail/112',
            '2020年30位30岁以下创业新贵': 'https://www.cyzone.cn/billboard/detail/104',
            '2020最具影响力&最值得关注的女性投资人': 'https://www.cyzone.cn/billboard/detail/126',
            '2020最值得关注的女性高层管理者': 'https://www.cyzone.cn/billboard/detail/127',
            '2020最值得关注的女性创业者': 'https://www.cyzone.cn/billboard/detail/120',
            '2019年度投资人': 'https://www.cyzone.cn/billboard/detail/83',
            '2019年度创业者': 'https://www.cyzone.cn/billboard/detail/152',
            '2019最值得关注的女性创业者': 'https://www.cyzone.cn/billboard/detail/118',
            '2019年40位40岁以下投资人': 'https://www.cyzone.cn/billboard/detail/111',
            '2019年30位30岁以下创业新贵': 'https://www.cyzone.cn/billboard/detail/103',
            '2018年度天使投资人': 'https://www.cyzone.cn/billboard/detail/82',
            '2018最值得关注的女性创业者': 'https://www.cyzone.cn/billboard/detail/146',
            '2018年40位40岁以下投资人': 'https://www.cyzone.cn/billboard/detail/110',
            '2018年度创业者': 'https://www.cyzone.cn/billboard/detail/71',
            '2018年30位30岁以下创业新贵': 'https://www.cyzone.cn/billboard/detail/102',
            '2017年度天使投资人': 'https://www.cyzone.cn/billboard/detail/81',
            '2017年40位40岁以下投资人': 'https://www.cyzone.cn/billboard/detail/109',
            '2017年度创业者': 'https://www.cyzone.cn/billboard/detail/70',
            '2017最值得关注的女性创业者': 'https://www.cyzone.cn/billboard/detail/116',
            '2017年30位30岁以下创业新贵': 'https://www.cyzone.cn/billboard/detail/101',
            '2016年度天使投资人': 'https://www.cyzone.cn/billboard/detail/80',
            '2016年40位40岁以下投资人': 'https://www.cyzone.cn/billboard/detail/108',
            '2016年度创业者': 'https://www.cyzone.cn/billboard/detail/69',
            '2016最值得关注的女性创业者': 'https://www.cyzone.cn/billboard/detail/115',
            '2016年30位30岁以下创业新贵': 'https://www.cyzone.cn/billboard/detail/100',
            '2015年度天使投资人': 'https://www.cyzone.cn/billboard/detail/79',
            '2015年40位40岁以下投资人': 'https://www.cyzone.cn/billboard/detail/107',
            '2015年度创业者': 'https://www.cyzone.cn/billboard/detail/68',
            '2015最值得关注的女性创业者': 'https://www.cyzone.cn/billboard/detail/114',
            '2015年30岁以下创业新贵': 'https://www.cyzone.cn/billboard/detail/99',
            '2014年度天使投资人': 'https://www.cyzone.cn/billboard/detail/78',
            '2014年40位40岁以下投资人': 'https://www.cyzone.cn/billboard/detail/106',
            '2014年度创业者': 'https://www.cyzone.cn/billboard/detail/67',
            '2014最值得关注的女性创业者': 'https://www.cyzone.cn/billboard/detail/145',
            '2014年30岁以下创业新贵': 'https://www.cyzone.cn/billboard/detail/98',
            '2013年度天使投资人': 'https://www.cyzone.cn/billboard/detail/77',
            '2013年度创业者': 'https://www.cyzone.cn/billboard/detail/66',
            '2013年40岁以下投资人': 'https://www.cyzone.cn/billboard/child/7500704',
            '2013最值得关注的女性创业者': 'https://www.cyzone.cn/billboard/detail/113',
            '2013年30岁以下创业新贵': 'https://www.cyzone.cn/billboard/detail/97',
            '2012年度天使投资人': 'https://www.cyzone.cn/billboard/detail/76',
            '2012年度创业者': 'https://www.cyzone.cn/billboard/detail/65',
            '2012年30岁以下创业新贵': 'https://www.cyzone.cn/billboard/detail/96',
            '2011年度天使投资人': 'https://www.cyzone.cn/billboard/detail/75',
            '2011年度创业者': 'https://www.cyzone.cn/billboard/detail/64',
            '2011年30岁以下创业新贵': 'https://www.cyzone.cn/billboard/detail/95',
            '2010年度天使投资人': 'https://www.cyzone.cn/billboard/detail/74',
            '2010年度创业者': 'https://www.cyzone.cn/billboard/detail/63',
            '2009年度天使投资人': 'https://www.cyzone.cn/billboard/detail/73',
            '2009年度创业者': 'https://www.cyzone.cn/billboard/detail/62',
            '2008年度天使投资人': 'https://www.cyzone.cn/billboard/detail/72',
            '2008年度创业者': 'https://www.cyzone.cn/billboard/detail/61',
        }
        return title_url

    def start_requests(self):
        url = 'https://www.cyzone.cn/billboard'
        yield scrapy.Request(
            url=url,
            method='GET',
            headers=self.headers,
            callback=self.parse_list,
            errback=self.errback,
            dont_filter=True,
            cb_kwargs={'url': url},
        )

    def parse_list(self, response, url):
        title_url = self.get_title_url()
        root = etree.HTML(response.text)
        items_list = root.xpath('//div[@class="billboard-wrap page-billboard"]/div[@class="year-group"]')
        for items in items_list:
            for item in items.xpath('./div[2]/a'):
                urls = item.xpath('./@href')[0]
                urls = urljoin(url, urls)
                title = item.xpath('./div[2]/text()')[0]
                keywords = ['投资人', '创业先锋', '女性', '年度创业者', '创业新贵']
                if any(i in title for i in keywords):
                    title_url[title] = urls
        for title, url in title_url.items():
            yield scrapy.Request(
                url=url,
                method='GET',
                headers=self.headers,
                callback=self.parse_url,
                errback=self.errback,
                dont_filter=True,
                cb_kwargs={'title': title, 'urls': url},
            )

    def parse_url(self, response, title, urls):
        element = etree.HTML(response.text)
        items = element.xpath('//div[@class="list"]/div')
        if items:
            for item in items:
                img = item.xpath('./a/div[1]/div/@style')[0]
                img = re.search(r'\((.*?)\)', img).group(1) if img else None
                name = item.xpath('./a/div[2]/div[1]/text()')[0]
                position = item.xpath('./a/div[2]/div[2]/text()')
                position = re.sub(r'\s+|未公开', '', position[0]) if position else None
                data_data = {}
                data_data['rankings_title'] = title
                data_data['md5_value'] = hash_md5(title + name)
                data_data['name'] = name
                data_data['position'] = position
                yield data_data
        else:
            num = urls.split('/')[-1]
            url = f'https://apila.cyzone.cn/v3/base/rank/rankList?parent_guid={num}&size=500'
            yield scrapy.Request(
                url=url,
                method='GET',
                headers=self.headers,
                callback=self.get_urllist,
                errback=self.errback,
                dont_filter=True,
            )

    def get_urllist(self, response):
        json_data = response.json()
        items = json_data['data']['data']
        for item in items:
            url = 'https://www.cyzone.cn/billboard/detail/' + str(item['id'])
            title = item['title']
            date = item['published_at_for_display']  # 发布日期
            yield scrapy.Request(
                url=url,
                method='GET',
                headers=self.headers,
                callback=self.parse_url,
                errback=self.errback,
                dont_filter=True,
                cb_kwargs={'title': title, 'urls': url},
            )

    def errback(self, failure): self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
