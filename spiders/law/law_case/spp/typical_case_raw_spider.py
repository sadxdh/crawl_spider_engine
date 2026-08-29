import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.llm_kit import CustomLlmChat
from utils.tools import *
from spiders.law.law_case.spp.prompt import *
from utils.time_kit import *

class TypicalCaseRawSpider(BaseSpider):
    name = 'typical_case_raw'
    data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        },
        #'COOKIES_ENABLED': True  # 使用cookie字段必须得要
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0',
    }

    llm_parser = CustomLlmChat()

    @staticmethod
    def generate_url(page):
        base_url = 'https://www.spp.gov.cn/spp/zgjdxal/'
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
                href = href.replace('#1', "#2") if href.endswith('#1') else href
                publish_date = xpath_parse(row, './span/text()')
                detail_url = urljoin(response.url, href)
                detail_list = {'url': detail_url, 'publish_date': publish_date}
                yield scrapy.Request(
                    url=detail_url,
                    method='GET',
                    headers=self.headers,
                    callback=self.parse_detail,
                    cb_kwargs={'detail_list': detail_list},
                )

    def parse_detail(self, response, detail_list):
        publish_date = detail_list['publish_date']
        url = detail_list['url']
        html_text = response.text.encode(response.encoding).decode('utf-8')
        modules = self.extract_cases(html_text)

        for i, ps_list in enumerate(modules):
            logger.info(f"\n=== 模块 {i} ===")
            p_text = [p.get_text() for p in ps_list]
            p_text = '\n'.join(p_text)
            file_content = {'url': url, 'publish_date': publish_date, 'text': p_text}
            yield from self.parse_data(file_content)

    @staticmethod
    def extract_cases(html_text):
        # 案例分块
        soup = BeautifulSoup(html_text, 'html.parser')
        ps = soup.select('#fontzoom p')

        flag = 0

        pattern = r'^案例(?:[一二三四五六七八九十]+|\d+).*'
        pattern2 = r'^[一二三四五六七八九十]+、.*案$'

        # 找出所有案号 p 的索引
        case_indices = []
        for i, p in enumerate(ps):
            text = p.get_text(strip=True)
            if match_text(text, pattern):
                flag = 1
                case_indices.append(i)
            if match_text(text, pattern2):
                flag = 1
                case_indices.append(i)
            if '【关键词】' in text and flag == 0:
                case_indices.append(i)

        # 案例数量
        n = len(case_indices)
        modules = []

        if n > 0:
            # 每个案例：标题 + 后续内容
            for idx, start_i in enumerate(case_indices):
                if idx == n - 1:
                    # 最后一个案例：到末尾
                    end_i = len(ps)
                else:
                    # 下一个案例的标题前一行
                    if flag == 2:
                        end_i = case_indices[idx + 1] - 1
                    else:
                        end_i = case_indices[idx + 1]

                if flag == 0:
                    title_i = start_i - 1  # 标题在案号前一行
                    case_ps = [ps[title_i]] + ps[start_i:end_i]
                else:
                    case_ps = ps[start_i:end_i]
                modules.append(case_ps)
        else:
            modules.append(ps)
        return modules

    def parse_data(self, data):
        url = data['url']
        publish_date = data['publish_date']
        text = data['text']

        res = self.llm_parser.chat(prompt=prompt, text=text)
        res = self.clean_llm_result(res)
        res = json.loads(res)

        title = res['title']
        key_words = res['keyword']
        court_name = res['court_name']
        basic_facts = res['basic_facts']
        judgment_reason = res['judgment_reason']
        judgment_essence = res['judgment_essence']
        judgment_mean = res['judgment_mean']
        related_info = res['related_info']

        main_info_list = [court_name, publish_date]
        main_info_list = [i for i in main_info_list if i]
        main_info = '/'.join(main_info_list)

        md5_value = hash_md5(title + "人民检察院案例")

        # item = LawCaseItem()
        items = {}
        # item.spider_name = self.spider_name
        items['web_name'] = "人民检察院案例"
        items['web_url'] = url
        items['main_type'] = 4  # 检察院案例
        items['title'] = title
        items['main_info'] = main_info
        items['judgment_essence'] = judgment_essence
        items['md5_value'] = md5_value
        # insert_data(table='spider_case_raw', data=item
        items['_table'] = 'spider_case_raw'
        yield items

        # item_main = CaseParseMainItem()
        # item_main.spider_name = self.spider_name
        # item_main.web_name = "人民检察院案例"
        # item_main.web_url = url
        # # item_main.storage_no = storage_no
        # item_main.case_level = 2
        # item_main.court_name = court_name
        # item_main.key_words = key_words
        # item_main.basic_facts = basic_facts
        # item_main.judgment_reason = judgment_reason
        # item_main.judgment_essence = judgment_essence
        # item_main.judgment_mean = judgment_mean
        # item_main.related_info = related_info
        # item_main.md5_value = md5_value
        # insert_data(table='case_parse_main', data=item_main)

    def clean_llm_result(self, res):
        if not res:
            return ""

        res = re.sub(r"<think>.*?</think>", "", res, flags=re.S).strip()
        res = re.sub(r"^```(?:json)?", "", res, flags=re.I).strip()
        res = re.sub(r"```$", "", res).strip()

        match = re.search(r"\{.*\}", res, flags=re.S)
        if match:
            return match.group(0)

        return res

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')