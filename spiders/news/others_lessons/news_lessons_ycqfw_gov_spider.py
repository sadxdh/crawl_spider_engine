import hashlib, scrapy
import re
from urllib.parse import urljoin, urlsplit
import ast

from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class NewsLessonsYcqfwGovSpider(BaseSpider):
    name = 'news_lessons_ycqfw_gov'
    data_table = 't_spider_discipline_article'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 5, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        },
        # 'RETRY_ENABLED': True,
        # "RETRY_HTTP_CODES": [566],
        # "RETRY_TIMES": 3,  # 失败重试
        #'COOKIES_ENABLED': True  # 使用cookie字段必须得要
    }
    proxy_type = 'long_proxy'

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
        "sec-ch-ua": "\"Not=A?Brand\";v=\"99\", \"Google Chrome\";v=\"151\", \"Chromium\";v=\"151\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            if page == 1:
                base_url = 'https://www.ycqfw.gov.cn/html/hkjw/qfsy/index.html'
            else:
                base_url = f'https://www.ycqfw.gov.cn/html/hkjw/qfsy/{page}.html'
            yield scrapy.Request(
                url=base_url,
                headers=self.headers,
                callback=self.parse_list,
                dont_filter=True,
            )


    def parse_list(self, response):
        soup = BeautifulSoup(response.text, 'lxml')
        for item in soup.select('.zw>ul>li'):
            detail_url = urljoin(response.url, item.a['href'])
            publish_time = item.span.text.strip().replace('[', '').replace(' ]', '').replace(']', '')
            title = item.a.text.replace("\xa0", "").lstrip("·").strip()
            yield scrapy.Request(
                url=detail_url,
                headers=self.headers,
                callback=self.parse_details,
                cb_kwargs={'detail_url': detail_url, 'title': title, 'publish_time': publish_time}
            )

    def parse_details(self, response, detail_url, title, publish_time):
        response_text = self.complete_links(response.text, detail_url)
        soup = BeautifulSoup(response_text, 'lxml')
        image_urls = []
        if soup.select('.contents'):
            content = str(soup.select('.contents')[0])
            for img in soup.select('.contents img'):
                image_urls.append(img['src'])
        else:
            content = None
            self.log_info(f'内容提取失败: {detail_url}')

        md5_value = hash_md5(detail_url)
        if content:
            main_item = {}
            main_item['article_type'] = 2 # 文章类型：1‑警示教育，2‑他山之石
            main_item['title'] = title  # 文章标题
            main_item['publish_time'] = publish_time # 发布时间
            main_item['content'] = content  # 文章正文
            main_item['article_origin_url'] = detail_url # 文章原链接
            main_item['md5_value'] = md5_value
            main_item['web_name'] = '中共海口市纪律检查委员会'
            main_item['_table'] = "t_spider_discipline_article"
            yield main_item

        for img in image_urls:
            img_item = {}
            img_item['announcement_url'] = img
            img_item['announcement_title'] = title
            img_item['md5_value_details'] = md5_value
            img_item['md5_value'] =  hash_md5(img + md5_value)
            img_item['media_type'] = 'image'
            img_item['_table'] = "t_spider_discipline_article_oss"
            yield img_item

    # 补齐文本里面的所有链接
    def complete_links(self, text, base_url):
        parsed = urlsplit(base_url)
        site_root = f"{parsed.scheme}://{parsed.netloc}/"

        def build_url(link):
            link = link.strip()

            # 已经是完整链接或特殊链接
            if re.match(r"^(?:https?:|data:|mailto:|tel:|javascript:|#)", link, re.I):
                return link

            # //example.com/a.jpg
            if link.startswith("//"):
                return f"{parsed.scheme}:{link}"

            # 该网站的 uploadfile 是相对于网站根目录
            if link.lstrip("/").lower().startswith("uploadfile/"):
                return urljoin(site_root, link.lstrip("/"))

            # 其他相对链接正常根据当前页面补全
            return urljoin(base_url, link)

        def replace_url(match):
            prefix = match.group("prefix")
            quote = match.group("quote")
            link = match.group("link")

            return f"{prefix}{quote}{build_url(link)}{quote}"

        # 处理 HTML 的 href、src 属性
        text = re.sub(
            r'(?P<prefix>\b(?:href|src)\s*=\s*)'
            r'(?P<quote>["\'])'
            r'(?P<link>[^"\']+)'
            r'(?P=quote)',
            replace_url,
            text,
            flags=re.IGNORECASE,
        )

        # 处理 Markdown 链接
        text = re.sub(
            r'(\]\()(?P<link>[^)\s]+)(\))',
            lambda match: (
                f"{match.group(1)}"
                f"{build_url(match.group('link'))}"
                f"{match.group(3)}"
            ),
            text,
        )

        return text


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')