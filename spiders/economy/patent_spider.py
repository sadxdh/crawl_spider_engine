"""专利/集成电路公告 → ml_org_patent_basic_info_file_upload
数据来源: www.cnipa.gov.cn/col/col164 (集成电路布图设计公告)
列表页: 数据在 <script type="text/xml"> CDATA 中，jpage 动态加载
详情页: <meta name="description"> 包含每条专利的登记号/公告号/名称
"""
import re, scrapy
from lxml import etree
from spiders.base_spider import BaseSpider
from utils.tools import *
import time

class PatentSpider(BaseSpider):
    name = 'economy_patent'
    data_table = 'layout_design'
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        "Accept": "application/xml, text/xml, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
        "X-Requested-With": "XMLHttpRequest",
    }

    @staticmethod
    def get_type(title):
        if not title:
            return 0
        title_str = title.extract_first() if hasattr(title, 'extract_first') else str(title)

        type_keywords = {
            2: "专有权事务公告",  # 优先级最高
            3: "终止公告",
            1: "专有权公告"
        }
        for type_num, keyword in type_keywords.items():
            if keyword in title_str:
                return type_num
        return 0

    def start_requests(self):
        data = {
            "col": "1",
            "webid": "1",
            "path": "https://www.cnipa.gov.cn/",
            "columnid": "164",
            "sourceContentType": "1",
            "unitid": "669",
            "webname": "国家知识产权局",
            "permissiontype": "0"
        }
        # 循环翻页
        for page in range(self.start_page, self.end_page + 1):
            start_record = (page - 1) * 45 + 1
            end_record = page * 45
            # 计算当前页的起始和结束记录
            url = f"https://www.cnipa.gov.cn/module/web/jpage/dataproxy.jsp?startrecord={str(start_record)}&endrecord={str(end_record)}&perpage=15"
            self.log_info(f"正在处理第 {page + 1} 页 (记录 {start_record} 到 {end_record})")
            yield scrapy.FormRequest(
                url=url,
                method='post',
                headers=self.headers,
                formdata=data,
                callback=self.parse,
                dont_filter=True
            )

    def parse(self, response):
        try:
            cdata_pattern = r'<!\[CDATA\[(.*?)\]\]>'
            records = re.findall(cdata_pattern, response.text, re.DOTALL)
            for record in records:
                # 使用正则表达式直接提取链接和标题
                pattern = r'<a href="(.*?)"[^>]*>(.*?)</a>'
                matches = re.findall(pattern, record, re.DOTALL)
                for link, title in matches:
                    # 清理标题中的多余空白字符
                    title = re.sub(r'\s+', ' ', title).strip()
                    # logger.info(f"开始抓取标题为：{title} ，url为：{link} 的数据")
                    yield scrapy.FormRequest(
                        method='get',
                        url=link,
                        headers=self.headers,
                        callback=self.parse_detail,
                        dont_filter=True
                    )
            time.sleep(1)
        except Exception as e:
            self.log_error(f"处理翻页时出错: {e}")

    def parse_detail(self, response):
        """
        处理第二个介绍请求的响应，并整合所有数据
        """
        if response:
            try:
                title = response.xpath('//div[@class="content clearfix"]/div/h1/text()').get()
                announcement_type = self.get_type(title)
                content = "\n".join(response.xpath('//div[@class="article-content cont"]//text()').extract())
                items = {}
                source_url = response.url
                # 拍卖相关字段处理
                items['md5_value'] = hash_md5(source_url + title)
                items['title'] = title  # 标题
                items['source_url'] = source_url  # 来源
                items['content'] = content  # 内容
                items['announcement_type'] = announcement_type  # 内容
                yield items
            except Exception as e:
                self.log_error(f"详情页错误{e}, 响应数据：{response.text}")
                return None

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url}')
