import hashlib, scrapy
import ast
import re

from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *
from urllib.parse import urljoin, urlsplit

class NewsWarn12371CnSpider(BaseSpider):
    name = 'news_warn_12371_cn'
    data_table = 't_spider_discipline_article'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 1, 'DOWNLOAD_DELAY': 1,
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
        base_url = 'https://www.12371.cn/special/jsjy/'
        yield scrapy.Request(
            url=base_url,
            headers=self.headers,
            callback=self.parse_list
        )

    def parse_list(self, response):
        pattern = r'itemELMT\d+\s*=\s*(\[\{.+?\}\]);'
        data_list_str = re.search(pattern, response.text, re.DOTALL)
        if data_list_str:
            data_list = ast.literal_eval(data_list_str.group(1))
            for item in data_list:
                detail_url = item['link_add']
                title = item['title']
                yield scrapy.Request(
                    url=detail_url,
                    headers=self.headers,
                    callback=self.parse_details,
                    cb_kwargs={'detail_url': detail_url, 'title': title}
                )

    def parse_details(self, response, detail_url, title):
        response_text = self.complete_links(response.text, detail_url)
        soup = BeautifulSoup(response_text, 'lxml')
        image_urls = []
        if soup.select('#font_area'):
            content = str(soup.select('#font_area')[0])
            for img in soup.select('#font_area img'):
                image_urls.append(img['src'])
        elif soup.select('.bg_top_owner>.column_wrapper_1200>.com_800'):
            content = str(soup.select('.bg_top_owner>.column_wrapper_1200>.com_800')[-1])
            for img in soup.select('.bg_top_owner>.column_wrapper_1200>.com_800')[-1].select('img'):
                image_urls.append(img['src'])
        else:
            content = None
            self.log_info(f'内容提取失败: {detail_url}')

        md5_value = hash_md5(detail_url)
        if content:
            main_item = {}
            main_item['article_type'] = 1 # 文章类型：1‑警示教育，2‑他山之石
            main_item['title'] = title  # 文章标题
            main_item['publish_time'] = None # 发布时间
            main_item['content'] = content  # 文章正文
            main_item['article_origin_url'] = detail_url # 文章原链接
            main_item['md5_value'] = md5_value
            main_item['web_name'] = '共产党员网'
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

        # 获取视频链接
        html_video_url = self.get_video_url(response)
        if html_video_url:
            yield scrapy.Request(
                url=html_video_url,
                headers=self.headers,
                callback=self.parse_video_url,
                cb_kwargs={'md5_value': md5_value, 'title': title}
            )

    def parse_video_url(self, response, md5_value, title):
        json_data = json.loads(response.text)
        video_url = json_data.get('hls_url')
        if video_url:
            video_item = {}
            video_item['announcement_url'] = video_url
            video_item['announcement_title'] = title
            video_item['md5_value_details'] = md5_value
            video_item['md5_value'] = hash_md5(video_url + md5_value)
            video_item['media_type'] = 'video'
            video_item['_table'] = "t_spider_discipline_article_oss"
            yield video_item


    def get_video_url(self, response):
        try:
            pid = re.findall(r'var guid = "(.*?)";', response.text)[0]
            # 获取当前时间戳（取前10位）
            a = str(int(time.time()))
            r = "2049"
            s = "B5AE275A5C9CC2D729267410E8291CF0"
            # MD5 加密
            md5_str = a + r + "47899B86370B879139C08EA3B5E88267" + s
            i = hashlib.md5(md5_str.encode()).hexdigest().upper()
            # 拼接结果
            e = f"https://vdn.apps.cntv.cn/api/getHttpVideoInfo.do?pid={pid}&client=flash&im=0&tsp={a}&vn={r}&vc={i}&uid={s}&wlan="
            return e
        except:
            return None


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