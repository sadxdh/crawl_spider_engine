import urllib
from urllib.parse import urlencode
import scrapy
from scrapy import FormRequest
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *
import re, json


class YunGongPaiSpider(BaseSpider):
    name = 'yun_company_assert_gongpai'

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36',
    }
    data_table = 'assets_auction'
    custom_settings = {
        'CONCURRENT_REQUESTS': 1, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

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

    def start_requests(self):
        start_page, end_page = self.start_page, self.end_page
        for j in [1, 2, 4, 5, 6, 14, 15, 16]:
            for i in range(start_page, end_page + 1):
                headers = self.headers.copy()
                headers['Referer'] = f'https://zc.gpai.net/zc/zc_auction?productIndex={i}'
                url = "https://zc.gpai.net/zc/api/item/list"
                params = {
                    "info": json.dumps(
                        {
                            "channelId": 43,
                            "itemType": j,
                            "auctionModeList": None,
                            "assetClass": None,
                            "minPrice": "",
                            "maxPrice": "",
                            "pageNumber": i,
                            "pageSize": 20,
                        },
                        separators=(",", ":"),
                    ),
                }
                yield scrapy.Request(
                    url=f"{url}?{urlencode(params)}",
                    method='get',
                    headers=headers,
                    callback=self.parse,
                    dont_filter=True
                )

    def parse(self, response, *args, **kwargs):
        if response:
            try:
                items = response.json()
            except Exception as e:
                logger.warning(f"商品列表响应错误{e}数据：{response.text}")
                return None
        for item in items['data']['list']:
            itemId = item['itemId']
            headers = self.headers.copy()
            headers['Referer'] = f"https://zc.gpai.net/zc/detail?id={itemId}"
            url = "https://zc.gpai.net/zc/api/item/item"
            params = {
                "info": f"{{\"id\":\"{itemId}\"}}"
            }
            meta_data = {
                'itemId': itemId,
            }
            yield scrapy.Request(
                method='get',
                url=f"{url}?{urlencode(params)}",
                headers=headers,
                meta=meta_data,
                callback=self.parse_lot_details,
                dont_filter=True
            )

    def parse_lot_details(self, response):
        """
        处理第一个详情请求的响应
        """
        itemId = response.meta['itemId']
        if response:
            try:
                data_json = response.json()
            except Exception as e:
                logger.warning(f"商品详情页响应错误{e}数据：{response.text}")
                return None
        data = data_json['data']['item']
        itemName = data['itemName']  # 标题

        itemAccessory = data.get('itemAccessory')
        attachment_list = []
        if itemAccessory and itemAccessory.strip():
            itemAccessory = json.loads(itemAccessory)
            for attachment in list(itemAccessory):
                attachment_list.append(attachment.get('url'))

        item = {}
        # 拍卖相关字段处理
        item['md5_value'] = hash_md5(str(itemId) + itemName)
        item['auction_title'] = itemName  # 拍卖标题
        item['auction_status'] = data.get('value')  # 拍卖状态
        # 修复数值字段，确保为空时使用None而不是空字符串
        item['start_price'] = data.get("startPrice")  # 起拍价
        item['price_increase_range'] = data.get("markupRange")  # 加价幅度
        item['evaluation_price'] = data.get("eamrPrice")  # 评估价
        item['bid_cycle'] = data.get("auctionPeriod")  # 竞价周期
        item['bond'] = data.get("depositValue")  # 保证金
        item['delay_period'] = data.get("delayedTime")  # 延迟周期
        item['reserve_price'] = None  # 保留价(原数据中未包含此字段)
        item['subject_matter_location'] = data.get("addressDetail")  # 标的所在地
        item['bid_start_time'] = data.get("beginTime", "")  # 竞价开始时间
        item['bid_end_time'] = data.get("endTime", "")  # 竞价结束时间
        item['disposal_unit'] = self.extract_company_name(itemName)  # 处置单位
        # 修复：将图片列表转换为逗号分隔的字符串
        item['subject_matter_img'] = data.get("itemPicture").replace('|', ',') if data.get(
            "itemPicture") else ''  # 标的物图片
        item['subject_matter_introduce'] = data_json['data'].get('itemDescribe')  # 标的物介绍
        item['subject_matter_attachment'] = ','.join(attachment_list) if attachment_list else ''  # 标的物附件
        item['bid_announcement'] = data_json['data'].get('notice')  # 竞买公告
        item['bid_notice'] = data_json['data'].get('biddingAgreement')  # 竞买需知
        item['source_url'] = f"https://zc.gpai.net/zc/detail?id={itemId}"  # 来源
        item['stage'] = data.get("auctionNumber")  # 拍卖阶段
        yield item
