"""胡润榜单爬虫 → rankings_information"""
import hashlib, scrapy;
from spiders.base_spider import BaseSpider
from utils.tools import *
import time
from urllib.parse import parse_qs, urlencode


# 网站改版了
class RankingsMHEnterpriseSpider(BaseSpider):
    name = 'economy_rankings_MH_enterprise'
    data_table = 'rankings_information'
    allowed_domains = ['www.hurun.net']
    custom_settings = {'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1}
    proxy_type = 'long_proxy'
    dedup_fields = ['md5_value']
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Referer': 'https://www.jiqizhixin.com/articles/2020-09-29-9',
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

    def parse_list2(self, etree_html, url, year):
        if year == '2019':
            xpath_items = '//section[@class="company-list"]/section'
            xpath_title = './div/h2/text()'
            xpath_datalist = './/div[@class="section-company__list"]/a'
            xpath_name = './/h3/text()'
            xpath_img = './/img/@src'
        elif year == '2018':
            xpath_items = '/html/body/div[contains(@class, "awards")]'
            xpath_title = './/h2/span/text()'
            xpath_datalist = './/div[@class="awards__items"]/div'
            xpath_name = './/h5/text()'
            xpath_img = './/image/@src'

        items = etree_html.xpath(xpath_items)
        for item in items[:3]:
            try:
                title_content = item.xpath(xpath_title)[0].replace(' ', '')
                url_content = f'「AI中国」机器之心{year}年度评选-{title_content}'
                datalist = item.xpath(xpath_datalist)
                for data in datalist:
                    name = data.xpath(xpath_name)[0] if data.xpath(xpath_name) else None
                    if name:
                        img = data.xpath(xpath_img)[0] if data.xpath(xpath_img) else None
                        announcename = name + img[-4:] if img else None
                        md5_value = hash_md5(title_content + name)
                        items = {}
                        items['md5_value'] = md5_value
                        items['url'] = url_content
                        items['rankings_title'] = title_content
                        items['rankings_name'] = name
                        items['source'] = '机械之心'
                        items['announcement_title'] = announcename
                        items['announcement_url'] = img
                        yield items
            except IndexError:
                error_msg = f'url: {url}, 未能找到预期的元素'
                self.log_error(error_msg)

    def start_requests(self):
        items = ['2018', '2019', '2020', '2021', '2022', '2023']
        for item in items:
            url = f'https://www.jiqizhixin.com/awards/{item}'
            title = f"{item}年度榜单"
            yield scrapy.Request(
                url=url,
                method='GET',
                headers=self.headers,
                errback=self.errback,
                dont_filter=True,
                callback=self.parse_year,
                cb_kwargs={'title': title, 'url': url},
            )

    def parse_year(self, response, title, url):
        etree_html = etree.HTML(response.text)
        if title in ['2020', '2021', '2022', '2023']:
            self.parse_list1(etree_html, url)
        elif title in ['2019', '2018']:
            self.parse_list2(etree_html, url, title)
        else:
            self.log_error(f'{title}页面解析错误,url:{url}')

    def parse_list1(self, etree_html, url):
        xpath_lists = """
        //div[@class="awards_2022-step__block"] |    
        //div[@class="index__rank__content-card"] | 
        //div[@class="award-list__content"]/a
        """
        contents = etree_html.xpath(xpath_lists)
        for content in contents:
            xpath_url = "./a/@href | ./@href"
            url_content = urljoin(url, content.xpath(xpath_url)[0])
            url_title = "./div/p/text() | ./div[1]/div/text()"
            title_content = '-'.join(content.xpath(url_title)).replace(' ', '')
            yield scrapy.Request(
                url=url_content,
                method='GET',
                headers=self.headers,
                errback=self.errback,
                dont_filter=True,
                callback=self.parse_list1_data,
                cb_kwargs={'title_content': title_content, 'url_content': url_content},
            )

    def parse_list1_data(self, response, title_content, url_content):
        etree_html = etree.HTML(response.text)
        item_xpath = """
                        //div[@class="content__card-area"]/div |
                        //div[@class="award-institutions"]/div |
                        //div[@class="soluton-award__solutions award-institutions"]/div
                     """
        items = etree_html.xpath(item_xpath)
        for item in items:
            name_xpath = """
                            ./div/p/text() | .//span/text() |
                            .//p[@class='card-name']/text() |
                            .//div[@class='solution__institution__name']/text()
                         """
            name = item.xpath(name_xpath)[0].replace(' ', '') if item.xpath(name_xpath) else None
            if name:
                img_xpath = """
                                ./div/img/@src |
                                ./div/img/@src |
                                .//img[@class='card-avatar']/@src |
                                .//img[contains(@alt, '')]/@src
                            """
                img = item.xpath(img_xpath)[0] if item.xpath(img_xpath) else None
                announcename = name + img[-4:] if img else None
                md5_value = hash_md5(title_content + name)
                items = {}
                items['md5_value'] = md5_value
                items['url'] = url_content
                items['rankings_title'] = title_content
                items['rankings_name'] = name
                items['source'] = '机械之心'
                items['announcement_title'] = announcename
                items['announcement_url'] = img
                yield items


    def errback(self, failure): self.log_error(f'请求失败: {failure.request.url} — {failure.value}')