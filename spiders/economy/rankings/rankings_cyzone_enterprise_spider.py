"""创业邦榜单爬虫 → rankings_information"""
import hashlib, scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *

class RankingsCyzoneEnterpriseSpider(BaseSpider):
    name = 'economy_rankings_cyzone_enterprise'
    data_table = 'rankings_information'
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
            '2021中国最受赞赏的投资机构': 'https://www.cyzone.cn/billboard/child/9596807',
            '2020年最受创业者认可的风险投资机构': 'https://www.cyzone.cn/billboard/child/7500707',
            '2020中国创新成长企业100强': 'https://www.cyzone.cn/billboard/detail/143',
            '2020中国新基建创新力量TOP100': 'https://www.cyzone.cn/billboard/detail/147',
            '2020中国医疗大健康创新企业80强': 'https://www.cyzone.cn/billboard/detail/124',
            '2020年中国新消费增长企业50强': 'https://www.cyzone.cn/billboard/detail/151',
            '2019中国创新成长企业100强': 'https://www.cyzone.cn/billboard/detail/37',
            '2019中国金融科技创新企业30强': 'https://www.cyzone.cn/billboard/detail/122',
            '2019年企业数字化_智能化创新榜': 'https://www.cyzone.cn/billboard/detail/56',
            '2019中国教育创新企业30强': 'https://www.cyzone.cn/billboard/detail/58',
            '2019中国大消费创新企业50强': 'https://www.cyzone.cn/billboard/detail/57',
            '2019中国医疗大健康创新企业50强': 'https://www.cyzone.cn/billboard/detail/60',
            '2018中国企业服务创新企业50强': 'https://www.cyzone.cn/billboard/detail/54',
            '2018中国创新成长企业100强': 'https://www.cyzone.cn/billboard/detail/50',
            '2018中国人工智能企业50强': 'https://www.cyzone.cn/billboard/detail/55',
            '2017中国企业服务创新企业50强': 'https://www.cyzone.cn/billboard/detail/52',
            '2017中国创新成长企业100强': 'https://www.cyzone.cn/billboard/detail/49',
            '2017中国人工智能企业50强': 'https://www.cyzone.cn/billboard/detail/53',
            '2016中国创新成长企业100强': 'https://www.cyzone.cn/billboard/detail/48',
            '2015中国创新成长企业100强': 'https://www.cyzone.cn/billboard/detail/47',
            '2014中国创新成长企业100强': 'https://www.cyzone.cn/billboard/detail/46',
            '2013中国创新成长企业100强': 'https://www.cyzone.cn/billboard/detail/45',
            '2012中国创新成长企业100强': 'https://www.cyzone.cn/billboard/detail/44',
            '2011中国创新成长企业100强': 'https://www.cyzone.cn/billboard/detail/43',
            '2010中国创新成长企业100强': 'https://www.cyzone.cn/billboard/detail/41',
            '2009中国创新成长企业100强': 'https://www.cyzone.cn/billboard/detail/38'
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
                if not any(i in title for i in keywords):
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
                name = item.xpath('./a/div[2]/div/text()')[0]
                md5_value = hash_md5(title + name)
                data_data = {}
                data_data['md5_value'] = md5_value
                data_data['url'] = urls
                data_data['rankings_title'] = title
                data_data['rankings_name'] = name
                data_data['source'] = '创业邦'
                data_data['announcement_title'] = name + '.png'
                data_data['announcement_url'] = img
                yield data_data

        else:
            num = urls.split('/')[-1]
            self.get_urllist(num)
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
