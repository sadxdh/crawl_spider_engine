"""财富中文网榜单爬虫 → rankings_information"""
import hashlib, scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *
import time

class RankingsFortuneChinaSpider(BaseSpider):
    name = 'economy_rankings_fortune_China'
    data_table = 'rankings_information'
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
    def parse_data1(self, etree_html, url, title_xpath_list, time_xpath_list):
        # 遍历XPath列表尝试获取标题
        for xpath in title_xpath_list:
            url_titles = etree_html.xpath(xpath)
            if url_titles:
                url_title = url_titles[0].strip()
                break
        # 遍历XPath列表尝试获取时间
        for xpath in time_xpath_list:
            url_times = etree_html.xpath(xpath)
            if url_times:
                url_time = url_times[0].strip()
                break
        else:
            # 文章中没有则尝试从url里提取
            match = re.search(r'/(\d{4}-\d{2})/(\d{2})/', url)
            url_time = f"{match.group(1)}-{match.group(2)}" if match else None

        return url_title, url_time

    def parse_data2(self, etree_html, tr):
        ranking = ''
        companyName = ''
        revenue = ''
        region = ''

        ranking_xpath_list = [
            './td[1]/text()',
            './td[1]/em/text()',
            './td/b/font/text()',
            './td/font/b/text()',
            './td[1]/b/text()',
            './td/b/text()',
            './td/em/text()',
        ]
        for xpath in ranking_xpath_list:
            url_ranking = tr.xpath(xpath)
            if url_ranking:
                # if url_ranking is not None and url_ranking[0].isdigit() and 1 <= int(url_ranking[0]) <= 500:
                xpath_ranking = url_ranking[0].strip()
                if xpath_ranking.isdigit():
                    # 匹配数字部分ranking
                    ranking = xpath_ranking
                    break
        companyName_xpath_list = [
            './td[2]/text()',
            './td/a/text()',
            './td[3]//text()',
            './td/b/text()',
            './td/b/a/text()',
        ]
        for xpath in companyName_xpath_list:
            url_companyName = tr.xpath(xpath)
            if url_companyName:
                if url_companyName[0] != '•':
                    if not re.match(r'^\d+(?:,\d{3})*(?:\.\d+)?$', url_companyName[0]):
                        xpath_companyName = "".join(url_companyName).strip()
                        if not (
                                xpath_companyName.isdigit() or
                                xpath_companyName == '--' or
                                xpath_companyName == '-' or
                                xpath_companyName == '.' or
                                xpath_companyName == ''):
                            companyName = xpath_companyName
                            break
                        else:
                            continue

        revenue_xpaths = ['./td[3]/text()', './td[4]/text()', './td[5]/text()', './td/b/text()']
        region_xpaths = ['./td[4]/text()', './td[5]/text()', './td[6]/text()', './td[3]/text()']

        for xpath in revenue_xpaths:
            value = tr.xpath(xpath)
            if value:
                url_revenue = value[0].strip()
                if url_revenue:
                    # 匹配字符串中的所有数字部分
                    xpath_revenue = re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?', url_revenue)
                    if xpath_revenue:
                        max_number = max(float(num.replace(',', '')) for num in xpath_revenue)
                        revenue = next((num for num in xpath_revenue if float(num.replace(',', '')) == max_number),
                                       None)
                        break
        for xpath in region_xpaths:
            value = tr.xpath(xpath)
            if value:
                region = value[0].strip()
                if region:
                    # 匹配字符串中的中文地区
                    chinese_regions = re.findall(r'[\u4e00-\u9fa5]+', region)
                    if chinese_regions:
                        region = chinese_regions[0]
                        break
        return ranking, companyName, revenue, region


    def start_requests(self):
        url = 'https://www.fortunechina.com/rankings/home.htm'
        yield scrapy.Request(
            url=url,
            headers=self.headers,
            callback=self.get_url_list,
            errback=self.errback
        )

    def get_url_list(self, response):
        parser = etree.HTMLParser(encoding='utf-8')
        etree_html = etree.fromstring(response.body, parser=parser)
        url_htmls = etree_html.xpath('/html/body/div[4]/div/div[2]')
        for url_html in url_htmls:
            # 三个板块，17个类别链接
            url_lists = url_html.xpath("//a[@class='tit']/@href")
            url_titles = url_html.xpath("//a[@class='tit']/text()")
            url_dicts = {title: url for title, url in zip(url_titles, url_lists)}
            # 网址类别的解析-排除个人类别
            url_dicts = {k: v for k, v in url_dicts.items() if
                         k not in ['中国最具影响力的商界女性', '全球最具影响力的商界女性',
                                   '全球40位40岁以下商界精英',
                                   '中国40位40岁以下的商界精英', '中国最佳设计榜']}
            for i in url_dicts.items():
                url_dict = i[1]
                yield scrapy.Request(
                    url=url_dict,
                    headers=self.headers,
                    errback=self.errback,
                    callback=self.parse_list,
                    dont_filter=True,
                    cb_kwargs={'url_dicts': url_dicts, 'url_dict': url_dict}
                )
    def parse_list(self, response, url_dicts, url_dict):
        urls = [v for v in url_dicts.values()]
        etree_html = etree.HTML(response.body)
        # 解析得到所有历史年份的url
        urls_datelist = etree_html.xpath('//div[@class="swiper-wrapper"]')
        for urls_dates in urls_datelist:
            urls_date = urls_dates.xpath('.//a/@href')
            # 网页抓取的链接不完整，需要将相对路径进行拼接转换为绝对路径
            for url in urls_date:
                urls.append(urljoin(url_dict, url))
        # 对抓取的url集合去重
        urls_list = list(set(urls))
        for url_urls in urls_list:
            time.sleep(2)
            yield scrapy.Request(
                url=url_urls,
                headers=self.headers,
                errback=self.errback,
                callback=self.parse_itme,
                dont_filter=True,
                cb_kwargs={'url': url_urls}
            )

    def parse_itme(self, response, url):
        """三个模块新数据与旧数据解析不一致，需要严格区分开，目前只抓取适配数据"""
        etree_html = etree.HTML(response.body)
        # insert_data(table='rankings_information', data=item)
        # 三大类模块可能的XPath表达式列表-标题
        title_xpath_list = [
            '//div[@class="inner-page-title"]/text()',
            '//div[@class="text-mod big"]/div/h2/text()',
            '//div[@class="title"]/h1/text()'
        ]
        # 三大类模块可能的XPath表达式列表-发布时间
        time_xpath_list = [
            '//div[@class="hf-intro"]/p/text()',
            '//div[@class="date"]/text()',
        ]
        url_title, url_time = self.parse_data1(etree_html, url, title_xpath_list, time_xpath_list)

        tr_list = etree_html.xpath('//tbody/tr')
        if tr_list:
            for tr in tr_list:
                ranking, companyName, revenue, region = self.parse_data2(etree_html, tr)
                items = {}
                items['md5_value'] = hash_md5(url_title + companyName)
                items['source'] = '财富中文网'
                items['rankings_title'] = url_title
                items['release_date'] = url_time
                items['ranking'] = ranking
                items['rankings_name'] = companyName
                items['url'] = url
                if '500强' in url_title:
                    # 500强榜单类单独解析
                    if ranking is not None and ranking.isdigit() and 1 <= int(ranking) <= 500:
                        if '世界' in url_title:
                            items['revenue'] = revenue
                            items['region'] = region
                            yield items
                        else:
                            items['revenue'] = revenue
                            yield items
                    else:
                        continue
                else:
                    # 其他类的字段剔除
                    items['industry'] = revenue
                    yield items
        else:
            items = {}
            items['source'] = '财富中文网'
            items['rankings_title'] = url_title
            items['release_date'] = url_time
            items['url'] = url
            # 特殊类别单独解析
            if '《财富》未来' in url_title:
                tr_list = etree_html.xpath('//p/strong/text()')
                for tr in tr_list[:49]:
                    ranking, companyName = tr.split('.', 1)
                    items['ranking'] = ranking
                    items['rankings_name'] = companyName
                    items['md5_value'] = hash_md5(url_title + companyName)
                    yield items
            elif '《财富》改变世界' in url_title:
                tr_list = etree_html.xpath('//p/strong/text()')
                for tr in tr_list[1:51]:
                    ranking, companyName = tr.split('.', 1)
                    items['ranking'] = ranking
                    items['rankings_name'] = companyName
                    items['md5_value'] = hash_md5(url_title + companyName)
                    yield items
            elif '《财富》亚洲未来' in url_title:
                tr_list = etree_html.xpath('//div[@class="word-zh"]//p/strong/text()')
                pattern = r"(\d+)\.(.*)"
                companies = [re.match(pattern, line).group(2).strip() for line in tr_list if re.match(pattern, line)]
                for ranking, companyName in enumerate(companies, start=1):
                    items['ranking'] = ranking
                    items['rankings_name'] = companyName
                    items['md5_value'] = hash_md5(url_title + companyName)
                    yield items


    def errback(self, failure): self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
