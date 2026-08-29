import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.law.law_case.spp.tool import *
from utils.tools import *
from utils.time_kit import *

class SppGuidingCasePraseSpider(BaseSpider):
    name = 'spp_guiding_case_prase'
    # data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0',
    }

    @staticmethod
    def generate_url(page):
        base_url = 'https://www.spp.gov.cn/spp/jczdal/'
        tail_url = 'index.shtml' if page == 1 else f'index_{page}.htm'
        url = base_url + tail_url
        return url

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            req_url = self.generate_url(page)
            yield scrapy.Request(
                url=req_url,
                method='GET',
                headers=self.headers,
                callback=self.parse_list,
            )

    def parse_list(self, response):
        result = response.text.encode(response.encoding).decode('utf-8')
        result = etree.HTML(result)
        rows = xpath_parse(result, '//ul[@class="li_line"]/li', return_list=True)
        if rows:
            for row in rows:
                href = xpath_parse(row, './a/@href')
                publish_date = xpath_parse(row, './span/text()')
                detail_url = urljoin(response.url, href)
                detail_list = {'url': detail_url, 'publish_date': publish_date}
                yield scrapy.Request(
                    url=detail_url,
                    method='GET',
                    headers=self.headers,
                    callback=self.parse_detail,
                    cb_kwargs={'detail_list': detail_list}
                )

    def parse_detail(self, response, detail_list):
        publish_date = detail_list['publish_date']
        url = detail_list['url']
        html_text = response.text.encode(response.encoding).decode('utf-8')
        modules = extract_cases(html_text)

        for i, (title, ps_list) in enumerate(modules):
            logger.info(f"\n=== 模块 {i}: {title} ===")
            p_text = [p.get_text(strip=True) for p in ps_list]
            p_text = format_modules(p_text)

            storage_no = self.handle_storage_no(p_text)
            court_name_all = select_content(p_text, query_word='办案检察院', return_next=False)
            court_name = court_name_all.split('：')[1] if court_name_all else None

            # main_info 信息拼接
            main_info_list = [storage_no, court_name_all, publish_date]
            main_info_list = [i for i in main_info_list if i]
            main_info = '/'.join(main_info_list)

            judgment_essence = select_content(p_text, query_word='要旨')
            md5_value = hash_md5(title + "人民检察院案例")

            # # item = LawCaseItem()
            # items = {}
            # # item.spider_name = self.spider_name
            # items['web_name'] = "人民检察院案例"
            # items['web_url'] = url
            # items['main_type'] = 4  # 检察院案例
            # items['title'] = title
            # items['main_info'] = main_info
            # items['judgment_essence'] = judgment_essence
            # items['md5_value'] = md5_value
            # # insert_data(table='spider_case_raw', data=item)
            # yield items

            # 详细内容
            key_words = select_content(p_text, query_word='关键词')
            basic_facts = select_content(p_text, query_word='基本案情')

            judgment_reason = (
                select_content(p_text, query_word='履职过程')
                or select_content(p_text, query_word='诉讼过程')
                or select_content(p_text, query_word='监督情况')
                or select_content(p_text, query_word='履职情况')
                or select_content(p_text, query_word='听证过程')
            )

            judgment_mean = (
                    select_content(p_text, query_word='典型意义')
                    or select_content(p_text, query_word='指导意义')
            )

            related_info = (
                    select_content(p_text, query_word='相关规定')
                    or select_content(p_text, query_word='相关法律规定')
                    or select_content(p_text, query_word='相关立法')
            )

            # item_main = CaseParseMainItem()
            item_mains = {}
            # item_main.spider_name = self.spider_name
            item_mains['web_name'] = "人民检察院案例"
            item_mains['web_url'] = url
            item_mains['storage_no'] = storage_no
            item_mains['case_level'] = 1
            item_mains['court_name'] = court_name
            item_mains['key_words'] = key_words
            item_mains['basic_facts'] = basic_facts
            item_mains['judgment_reason'] = judgment_reason
            item_mains['judgment_essence'] = judgment_essence
            item_mains['judgment_mean'] = judgment_mean
            item_mains['related_info'] = related_info
            item_mains['md5_value'] = md5_value
            # insert_data(table='case_parse_main', data=item_main)
            item_mains['_table'] = 'case_parse_main'
            yield item_mains

    @staticmethod
    def handle_storage_no(p_text):
        for i in p_text:
            if i.startswith('（检例第') and '号）' in i:
                return i.replace('（', '').replace('）', '')
        return None




    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')