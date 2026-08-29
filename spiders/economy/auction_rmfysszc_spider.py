"""法拍-人民法院诉讼资产 → entity_auction_court"""
import hashlib, re, scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *
from dateutil import parser

class AuctionRmfysszcSpider(BaseSpider):
    name = 'economy_auction_court'
    data_table = 'assets_auction'
    dedup_fields = ['md5_value']
    default_end_page = 3

    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        "X-Requested-With": "XMLHttpRequest",
    }

    @staticmethod
    def get_date(html_content):
        """
        时间提取方法
        """
        # 1. 提取纯文本
        try:
            selector = scrapy.Selector(text=html_content)
            texts = selector.xpath('//div[@id="pmgg"]//text()').getall()
            plain_text = ''.join([t.strip() for t in texts if t.strip()])
        except:
            # 备用方案：正则清理HTML
            plain_text = re.sub(r'<[^>]+>', '', html_content)
            plain_text = re.sub(r'\s+', '', plain_text)
        plain_text = plain_text.replace('：', ':')

        # time_pattern = r'(?:将于|于)\s*(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2})(?:时|:\d{2})\s*(?:起至|至)\s*(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2})(?:时|:\d{2})'
        time_pattern = r'(?:将于|于)?\s*(\d{4})年(\d{1,2})月(\d{1,2})日(?:上午|下午)?(\d{1,2})(?:时|:\d{2})?.*?(?:起至|至)\s*(\d{4})年(\d{1,2})月(\d{1,2})日(?:上午|下午)?(\d{1,2})(?:时|:\d{2})?'
        match = re.search(time_pattern, plain_text)
        if match:
            groups = match.groups()
            start_time = f"{groups[0]}年{int(groups[1])}月{int(groups[2])}日{int(groups[3])}时"
            end_time = f"{groups[4]}年{int(groups[5])}月{int(groups[6])}日{int(groups[7])}时"
            return start_time, end_time
        return None, None

    @staticmethod
    # 从字段中提取公司名的函数
    def extract_company_name(company_address):
        if not company_address:
            return None
        # 匹配常见的公司名称模式（以"公司"结尾的）
        company_patterns = [
            r'(.+?公司)',  # 匹配到"XX公司"即停止（非贪婪）
            r'(.+?有限公司)',  # 如果没有"公司"，再尝试匹配"XX有限公司"
            r'(.+?集团)',  # 最后尝试匹配"XX集团"
        ]
        for pattern in company_patterns:
            match = re.search(pattern, company_address)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def convert_to_standard_datetime(time_str):
        """
        将各种时间格式转换为标准日期时间格式

        Args:
            time_str (str): 各种格式的时间字符串，如 "2025年8月30日10时" 或 "2025-08-30 10:00:00" 等

        Returns:
            str: 格式化的时间字符串 'YYYY-MM-DD HH:MM:SS'，如果输入为空或解析失败则返回空字符串
        """
        if not time_str:
            return None

        try:
            # 处理中文时间格式，如 "2025年8月30日10时"
            if "年" in time_str and "月" in time_str and "日" in time_str:
                pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日(\d{1,2})时'
                match = re.search(pattern, time_str)

                if match:
                    year, month, day, hour = match.groups()
                    # 格式化为标准时间格式
                    standard_time = f"{year}-{int(month):02d}-{int(day):02d} {int(hour):02d}:00:00"
                    return standard_time
                else:
                    return ""

            # 处理其他标准时间格式，使用dateutil.parser
            else:
                dt = parser.parse(time_str)
                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                return formatted_time

        except (ValueError, TypeError, AttributeError, parser.ParserError):
            # 如果转换失败，返回空字符串
            return ""

    def start_requests(self):
        for j in [1, 2, 5, 6, 7, 8, 10, 11]:
            for i in range(self.start_page, self.end_page + 1):
                headers = self.headers.copy()
                headers['Referer'] = f'https://www.rmfysszc.gov.cn/projects.shtml'
                url = "https://www.rmfysszc.gov.cn/ProjectHandle.shtml"
                data = {
                    "type": str(j),
                    "name": "",
                    "area": "",
                    "xmxz": "0",
                    "state": "0",
                    "money": "",
                    "money1": "",
                    "number": "0",
                    "fid1": "",
                    "fid2": "",
                    "fid3": "",
                    "order": "0",
                    "page": str(i),
                    "include": "0"
                }
                yield scrapy.FormRequest(
                    url=url,
                    method='post',
                    headers=headers,
                    formdata=data,
                    callback=self.parse,
                    dont_filter=True
                )

    def parse(self, response, *args, **kwargs):
        task = response.meta['task']
        if response:
            try:
                html_json = response.json().get('html')
                response = scrapy.Selector(text=html_json)
            except Exception as e:
                self.log_error(f"资产商品列表响应错误:{e},数据：{response.text}")
                return None
        for item in response.xpath('//div[@class="product"]'):
            itemId = item.xpath('./@id').get()
            url = f"https://www.rmfysszc.gov.cn/statichtml/rm_obj/{itemId}.shtml"
            if item.xpath('.//div[@class="prod-guj"]//p[contains(text(),"开始时间")]'):
                status = "未开始"
            elif item.xpath('.//div[@class="prod-guj"]//p[contains(text(),"结束时间")]'):
                status = "已结束"
            elif item.xpath('.//div[@class="prod-guj"]//i[contains(text(),"预计剩余")]'):
                status = "进行中"
            else:
                status = "未知状态"
            meta_data = {
                'task': task,
                'itemId': itemId,
                'status': status,
            }
            yield scrapy.Request(
                method='get',
                url=url,
                headers=self.headers,
                meta=meta_data,
                callback=self.parse_lot_details,
                dont_filter=True
            )

    def parse_lot_details(self, response):
        """
        处理第一个详情请求的响应
        """
        task = response.meta['task']
        itemId = response.meta['itemId']
        status = response.meta['status']
        url = f"https://www.rmfysszc.gov.cn/statichtml/rm_obj/{itemId}.shtml"
        try:
            title = response.xpath('//div[@id="Title"]//text()').getall()
            title = ''.join(title).strip()
            price = response.xpath(
                '//div[@id="price"]//span[contains(text(),"起拍价")]/following-sibling::span[1]/text()').get()
            evaluation_price = response.xpath(
                '//div[@id="bg1"]//span[contains(text(),"评 估 值: ")]/descendant::span[1]/text()').get()
            reverse_price = response.xpath(
                '//div[@id="bg1"]//span[contains(text(),"保 证 金: ")]/descendant::span[1]/text()').get()
            attachment = response.xpath(
                '//div[@class="tcl" and contains(text(),"相关附件")]/following-sibling::div//a/@href').getall()
            img_src_list = response.xpath('//div[@id="zzsc"]//img/@src').getall()
            unit = response.xpath(
                '//div[@id="bg1"]//span[contains(text(),"法") and contains(text(),"院")]/div/span/text()').get()
            stage = response.xpath(
                '//div[@id="bg1"]//span[contains(text(),"处置阶段: ")]/descendant::span[1]/text()').get()
            stage = response.xpath(
                '//div[@id="bg1"]//span[contains(text(),"处置阶段: ")]/text()').get()
            if stage:
                stage = stage.split(": ")[1] if ": " in stage else stage
            else:
                stage = None

            pmgg_element = response.xpath('//div[@id="pmgg"]')
            if pmgg_element:
                pmgg_html = pmgg_element[0].get()  # 获取包含HTML标签的内容
                start_time, end_time = self.get_date(pmgg_html)

            jmxz_element = response.xpath('//div[@id="jmxz"]')
            if jmxz_element:
                jmxz_html = jmxz_element[0].get()

            bdjs_element = response.xpath('//div[@id="bdjs"]')
            if bdjs_element:
                bdjs_html = bdjs_element[0].get()

            items = {}
            # 拍卖相关字段处理
            items['md5_value'] = hash_md5(str(itemId) + title)
            items['auction_title'] = title  # 拍卖标题
            items['auction_status'] = status  # 拍卖状态
            # 修复数值字段，确保为空时使用None而不是空字符串
            items['start_price'] = price  # 起拍价
            items['price_increase_range'] = None  # 加价幅度
            items['evaluation_price'] = evaluation_price  # 评估价
            items['bid_cycle'] = None  # 竞价周期
            items['bond'] = reverse_price  # 保证金
            items['delay_period'] = None  # 延迟周期
            items['reserve_price'] = None  # 保留价(原数据中未包含此字段)
            items['subject_matter_location'] = unit  # 标的所在地
            items['bid_start_time'] = self.convert_to_standard_datetime(start_time)  # 竞价开始时间
            items['bid_end_time'] = self.convert_to_standard_datetime(end_time)  # 竞价结束时间
            items['disposal_unit'] = self.extract_company_name(title)  # 处置单位
            # 修复：将图片列表转换为逗号分隔的字符串
            items['subject_matter_img'] = ','.join(img_src_list) if img_src_list else ''  # 标的物图片
            items['subject_matter_introduce'] = bdjs_html  # 标的物介绍
            items['subject_matter_attachment'] = ','.join(attachment) if attachment else ''  # 标的物附件
            items['bid_announcement'] = pmgg_html  # 竞买公告
            items['bid_notice'] = jmxz_html  # 竞买需知
            items['source_url'] = url  # 来源
            items['stage'] = stage
            yield items
        except Exception as e:
            self.log_error(f"错误url：{url} 商品详情响应错误:{e},数据：{response.text}")

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
