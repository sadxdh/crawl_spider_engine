"""胡润榜单爬虫 → rankings_information"""
import hashlib, scrapy;
from spiders.base_spider import BaseSpider
from utils.tools import *
import time
from urllib.parse import parse_qs, urlencode


class RankingsHurunEnterpriseSpider(BaseSpider):
    name = 'economy_rankings_hurun_enterprise'
    data_table = 'rankings_information'
    allowed_domains = ['www.hurun.net']
    custom_settings = {'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1}
    proxy_type = 'long_proxy'
    dedup_fields = ['md5_value']
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Referer': 'https://www.hurun.net/zh-CN/Rank/HsRankDetails?pagetype=bob',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Priority': 'u=0, i',
    }

    def get_value_by_partial_key(self, d, *partial_keys):
        """
        通过部分键名获取字典中的值
        :param d: 字典
        :param partial_keys: 多个部分键名
        :return: 包含部分键名的键对应的值
        """
        for partial_key in partial_keys:
            for key, value in d.items():
                # 将键按 '_' 分割
                parts = key.split('_', 3)
                # 检查分割后的最后一个部分是否等于 partial_key
                if "_" + parts[3] == partial_key:
                    if value and value != '0':
                        return value
        return None

    def start_requests(self):
        url = 'https://www.hurun.net/zh-CN/Home/Index'
        yield scrapy.Request(
            url=url,
            method='GET',
            headers=self.headers,
            callback=self.parse_list,
            errback=self.errback,
            dont_filter=True,
        )

    def parse_list(self, response):
        url_dicts = {}
        etree_xpath = etree.HTML(response.body)
        urls_lists = etree_xpath.xpath('//ul[@class="dropdown-menu"]/li/a[@class="dropdown-item"]')
        for urls in urls_lists:
            urls_list = urljoin(response.url, urls.xpath('./@href')[0])
            titles_list = urls.xpath('./text()')[0].strip()
            url_dicts.update({titles_list: urls_list})

            # 网址类别的解析-找公司类url
        url_dicts = {k: v for k, v in url_dicts.items() if
                     k in ['胡润中国500强', '胡润世界500强',
                           '胡润全球独角兽榜', '全球瞪羚企业榜', '全球猎豹企业榜', '中国元宇宙潜力企业榜',
                           '胡润全球创投机构', '胡润品牌榜', '胡润在中国的外资及港澳台企业百强',
                           '胡润中国最具历史文化底蕴品牌榜', '胡润中国餐饮连锁榜', '中国预制菜生产企业百强',
                           '胡润中国食品行业百强榜', '胡润百亿潜力品牌榜', '中国数字技术算法算力百强榜',
                           '胡润中国葡萄酒酒庄50强']}
        urls = set(url_dicts.values())
        for url in urls:
            yield scrapy.Request(
                url=url,
                method='GET',
                headers=self.headers,
                callback=self.get_url_list,
                errback=self.errback,
                cb_kwargs={'url': url},
            )
    def get_url_list(self, response, url):
        urls = set()
        urls.add(url)
        url2 = set()
        etree_xpath = etree.HTML(response.body)
        end_urls = etree_xpath.xpath('//div[@class="form-group"]/select/option[not(@selected)]')
        for end_url in end_urls:
            new_url = urljoin(url, end_url.xpath('./@value')[0])
            if new_url and new_url not in urls:
                url2.add(new_url)
        urls.update(url2)
        urls_lists = urls
        for url_url in urls_lists:
            yield scrapy.Request(
                url=url_url,
                method='GET',
                headers=self.headers,
                callback=self.parse_url,
                errback=self.errback,
                cb_kwargs={'url': url_url},
            )

    def parse_url(self, response, url):
        etree_xpath = etree.HTML(response.body)
        num = etree_xpath.xpath('//div[@class="form-group"]/select/option[@selected]/@value')[0]
        datas = etree_xpath.xpath('//div[@class="card-body"]/h5')
        for data in datas:
            title = data.xpath('./span[1]/text()')[0].strip() + data.xpath('./span[3]/text()')[0].strip()
        parsed_url = urlparse(url)
        # 修改路径和查询参数
        num = parse_qs(urlparse(num).query)['num'][0]
        new_query_params = {
            'num': num,
            'search': '',
            'offset': '0',
            'limit': '1500'  # 1452
        }
        new_url = parsed_url._replace(path=parsed_url.path + 'List', query=urlencode(new_query_params))
        data_url = new_url.geturl()
        yield scrapy.Request(
            url=data_url,
            method='GET',
            headers=self.headers,
            callback=self.parse_itme,
            errback=self.errback,
            cb_kwargs={'title': title, 'url': url},
        )

    def parse_itme(self, response, title, url):
        data = response.json()
        for row in data['rows']:
            ranking = self.get_value_by_partial_key(row, '_Ranking')
            comname = self.get_value_by_partial_key(row, '_ComName_Cn', '_BrandName_Cn')
            industry = self.get_value_by_partial_key(row, '_Industry_Cn')
            value = self.get_value_by_partial_key(row, '_Wealth')
            region = self.get_value_by_partial_key(row, '_ComHeadquarters_Cn', '_Headquarters_Cn',
                                                   '_CountryRegion_Cn', '_ComHead_Cn', '_Country_Cn')
            if region:
                region = region.replace('-', '')
            items = {}
            items['md5_value'] = hash_md5(title + comname)
            items['source'] = '胡润百富网'
            items['rankings_title'] = title
            items['ranking'] = ranking
            items['rankings_name'] = comname
            items['url'] = url
            items['industry'] = industry
            items['brand_value'] = value
            items['region'] = region
            yield items

    def errback(self, failure): self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
