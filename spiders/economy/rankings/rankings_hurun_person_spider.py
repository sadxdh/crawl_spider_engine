"""胡润榜单爬虫 → rankings_information"""
import hashlib, scrapy;
from spiders.base_spider import BaseSpider
from utils.tools import *
import time
from urllib.parse import parse_qs, urlencode


class RankingsHurunPersonSpider(BaseSpider):
    name = 'economy_rankings_hurun_person'
    data_table = 'personal_rankings'
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
                if partial_key in key:
                    if value and value != 0:
                        return value
        return ''

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
                     k in ['胡润百富榜', '胡润全球富豪榜',
                           '胡润女企业家榜', '胡润U40青年企业家榜', '胡润全球白手起家U40富豪榜',
                           '胡润Under30s创业领袖榜', '胡润美国U30创业领袖', '胡润U35中国创业先锋',
                           '胡润U40中国创业先锋', '胡润·平安中国好医生榜', '胡润国际理财规划顾问TOP100']}
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
        limit = '3000' if title == '2017年胡润-平安中国好医生榜' else '10000'
        new_query_params = {
            'num': num,
            'search': '',
            'offset': '0',
            'limit': limit
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
        if title in ['2017年胡润-平安中国好医生榜', '2021年胡润Under30s创业领袖',
                     '2023年胡润Under30s创业先锋',
                     '2022年胡润Under30s创业领袖', '2018年胡润Under30s创业领袖',
                     '2020年胡润Under30s创业领袖']:
            ranking = None
        else:
            ranking = True
        for row in data['rows']:
            name = self.get_value_by_partial_key(row, '_ChaName_Cn', 'Name_Cn')
            en_name = self.get_value_by_partial_key(row, '_ChaName_En', 'Name_En')
            position = self.get_value_by_partial_key(row, '_Hospital_Cn') + \
                       self.get_value_by_partial_key(row, '_Depart_Cn') + \
                       self.get_value_by_partial_key(row, '_Title_Cn')
            if ranking:
                ranking = self.get_value_by_partial_key(row, '_Ranking', '_ID')
            items = {}
            items['md5_value'] = hash_md5(title + name)
            items['rankings_title'] = title
            items['ranking'] = ranking
            items['name'] = name
            items['en_name'] = en_name
            items['position'] = position
            yield items

    def errback(self, failure): self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
