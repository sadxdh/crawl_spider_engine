import time
from scrapy import FormRequest
import re
from dateutil import parser
from spiders.base_spider import BaseSpider
from utils.tools import *
import time
from utils.time_kit import *


class YunZhongPaiSpider(BaseSpider):
    name = 'yun_company_assert_zhongpai'
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36',
    }
    data_table = 'assets_auction'
    custom_settings = {
        'CONCURRENT_REQUESTS': 4, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    @staticmethod
    def get_status(status):
        status_map = {
            "0": "即将开始",
            "1": "进行中",
            "2": "流拍",
            "3": "成交",
            "4": "撤拍",
        }
        status = status_map.get(status, "") if status else None
        return status

    @staticmethod
    def extract_company_name(company_address):
        if not company_address:
            return None
        # 匹配常见的公司名称模式（以"公司"结尾的）
        company_patterns = [
            r'[\u4e00-\u9fa5]{2,30}有限公司',  # 有限公司
            r'[\u4e00-\u9fa5]{2,30}公司',  # 公司
            r'[\u4e00-\u9fa5]{2,30}集团',  # 集团
        ]
        for pattern in company_patterns:
            match = re.search(pattern, company_address)
            if match:
                return match.group(0)
        return None

    @staticmethod
    def get_current_timestamp(offset=1):
        """
        返回当前毫秒级时间戳
        Args:
            offset (int): 时间戳偏移量（毫秒），默认为0
        Returns:
            str: 毫秒级时间戳字符串
        """
        if offset == 1:
            return str(int(time.time() * 1000))
        else:
            return str(int(time.time() * 1000) + 600)

    @staticmethod
    def convert_timestamp_to_datetime(timestamp):
        """
        将毫秒级时间戳转换为标准日期时间格式
        Args:
            timestamp (str or int): 毫秒级时间戳
        Returns:
            str: 格式化的时间字符串 'YYYY-MM-DD HH:MM:SS'，如果输入为空则返回空字符串
        """
        if not timestamp:
            return None
        try:
            # 如果是字符串，先转换为整数
            if isinstance(timestamp, str):
                timestamp = int(timestamp)

            # 如果是毫秒级时间戳，需要除以1000转换为秒级
            if timestamp > 1000000000000:  # 判断是否为毫秒级时间戳
                timestamp = timestamp // 1000

            # 转换为datetime对象，然后格式化为字符串
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, OSError, TypeError):
            # 如果转换失败，返回空字符串
            return ""

    def start_requests(self):
        start_page, end_page = self.start_page, self.end_page
        # for asset_type in [0, 1, 2, '']:
        for asset_type in [0]:
            if asset_type == 0:
                url = "https://paimai.caa123.org.cn/paimai-web/lots/recyclable/combination"
                i_list = [20]
            elif asset_type == '':
                url = "https://paimai.caa123.org.cn/paimai-web/lots/viechle/combination"
                i_list = [5]
            else:
                url = "https://paimai.caa123.org.cn/paimai-web/lots/combination"
                i_list = [6, 20, 18, 7, 8]
            for i in i_list:
                for j in range(start_page, end_page + 1):
                    params = {
                        "start": str(j),
                        "count": "20",
                        "sortName": "",
                        "sortOrder": "",
                        "name": "",
                        "status": "",
                        "type": str(asset_type),
                        "provinceCode": "",
                        "cityCode": "",
                        "areaCode": "",
                        "priceMin": "",
                        "priceMax": "",
                        "isRestricted": "",
                        "canLoan": "",
                        "standardType": str(i),
                        "secondaryType": "",
                        "term": "",
                        "startTime": "",
                        "endTime": "",
                        "time": self.get_current_timestamp(1),
                        "_": self.get_current_timestamp(2)
                    }
                    if asset_type == 0:
                        params.pop("type", None)  # 删除type键
                    if asset_type == '':
                        params['secondaryType'] = "4"
                    yield FormRequest(
                        url=url,
                        method='get',
                        headers=self.headers,
                        formdata=params,
                        callback=self.parse,
                        dont_filter=True
                    )

    def parse(self, response, *args, **kwargs):

        if response:
            try:
                items = response.json()
            except Exception as e:
                logger.warning(f"响应1错误：{e}，数据：{response.text}")
                return None
            for item in items["items"]:
                try:
                    id = item["id"].split("-")[0]
                except:
                    continue
                url_select = 1 if id == "zz" else 2
                lotId = item["lotId"]
                meetId = item["meetId"]
                params_2 = {
                    "time": self.get_current_timestamp(1),
                    "_": self.get_current_timestamp(2)
                }
                headers = self.headers.copy()
                headers["Referer"] = (f"https://paimai.caa123.org.cn/pages/financeassets/financelotdetail.html?"
                                      f"meetId={meetId}&lotId={lotId}")
                if url_select == 1:
                    url_2 = f"https://paimai.caa123.org.cn/paimai-web/zz/lot?lotId={lotId}"
                    params_2["lotId"] = str(lotId)
                else:
                    url_2 = f"https://paimai.caa123.org.cn/paimai-web/lot/{lotId}"

                # 传递原始数据到下一个请求
                meta_data = {
                    'url_select': url_select,
                    'lotId': lotId,
                    'meetId': meetId,
                }

                yield FormRequest(
                    method='get',
                    url=url_2,
                    headers=self.headers,
                    formdata=params_2,
                    meta=meta_data,
                    callback=self.parse_lot_details,
                    dont_filter=True
                )

    def parse_lot_details(self, response):
        """
        处理第一个详情请求的响应
        """
        lotId = response.meta['lotId']
        meetId = response.meta['meetId']
        url_select = response.meta['url_select']
        if response:
            try:
                data = response.json()
                if data.get("id", "") == 1888:
                    logger.info(f"检测到id为1888：数据来源为中拍平台，响应错误，丢弃数据")
                    return None
            except Exception as e:
                logger.warning(f"响应2错误：{e}，数据：{response.text}")
                return None
            lot_info = {
                "name": data.get("name", ""),
                "lotStatus": data.get("lotStatus", ""),
                "startPrice": data.get("startPrice", ""),
                "rateLadder": data.get("rateLadder", ""),
                "auctionType": data.get("auctionType", ""),
                "assessPrice": data.get("assessPrice", ""),
                "term": data.get("term", ""),
                "cashDeposit": data.get("cashDeposit", ""),
                "delayTime": data.get("delayTime", ""),
                "position": data.get("position", ""),
                "supervisionUnit": data.get("court", ""),
                "startTime": data.get("startTime", ""),
                "endTime": data.get("endTime", ""),
            }

            params_3 = {
                "time": self.get_current_timestamp(1),
                "_": self.get_current_timestamp(2)
            }
            # 准备第三个请求
            headers = self.headers.copy()
            if url_select == 1:
                url_3 = f"https://paimai.caa123.org.cn/paimai-web/zz/lot/introduction?lotId={lotId}"
                lot_info['source_url'] = f"https://paimai.caa123.org.cn/pages/own/lotdetail.html?lotId={lotId}"
                params_3["lotId"] = str(lotId)
                headers["Referer"] = f"https://paimai.caa123.org.cn/pages/own/lotdetail.html?lotId={lotId}"
            else:
                url_3 = f"https://paimai.caa123.org.cn/paimai-web/lot/{lotId}/introduction?"
                lot_info['source_url'] = (f"https://paimai.caa123.org.cn/pages/financeassets/financelotdetail.html?"
                                          f"meetId={meetId}&lotId={lotId}")

                headers["Referer"] = (f"https://paimai.caa123.org.cn/pages/financeassets/financelotdetail.html?"
                                      f"meetId={meetId}&lotId={lotId}&_=61CDAA251045E773CA05AD3027B40A28")

            # 传递已获取的数据到下一个请求
            meta_data = {
                'lotId': lotId,
                'meetId': meetId,
                'lot_info': lot_info,  # 传递第二个请求获取的数据
            }

            yield FormRequest(
                method='get',
                url=url_3,
                headers=headers,
                formdata=params_3,
                meta=meta_data,
                callback=self.parse_detail,
                dont_filter=True
            )

    def parse_detail(self, response):
        """
        处理第三个请求的响应，并整合所有数据
        """
        lot_info = response.meta['lot_info']
        lotId = response.meta['lotId']
        if response:
            try:
                introduce = response.json()
            except Exception as e:
                logger.warning(f"响应3错误：{e}，数据：{response.text}")
                return None
            introduction_info = {
                "content": introduce.get("content", "") if introduce.get("content") else introduce.get("noticeContent",
                                                                                                       ""),
                "guidance": introduce.get("guidance", "") if introduce.get("guidance") else introduce.get("remark", ""),
                "describe": introduce.get("describe", "") if introduce.get("describe") else introduce.get("description",
                                                                                                          ""),
                "position": introduce.get("position", "")
            }
            # 处理附件链接
            attachment_list = []

            attachments = introduce.get("enclosure") or introduce.get("enclosures", [])
            if attachments and isinstance(attachments, list):
                for attachment in attachments:
                    if isinstance(attachment, dict):
                        filepath = attachment.get("filePath", "")
                        if filepath:  # 确保filepath不为空
                            attachment_list.append(urljoin(response.url, filepath))
            # 处理图片链接
            jpg_list = []
            item_jpg = introduce.get("oriPics") or introduce.get("pictures", [])
            if item_jpg and isinstance(item_jpg, list):
                for jpg in item_jpg:
                    if isinstance(jpg, dict):
                        filepath = jpg.get("filePath", "")
                        if filepath:  # 确保filepath不为空
                            jpg_list.append(f"https://paimai.caa123.org.cn/{filepath}")

            title = lot_info.get("name", "")
            auction_status = lot_info.get("lotStatus", "")
            item = {}
            # 拍卖相关字段处理
            item['md5_value'] = hash_md5(str(lotId) + title)
            item['auction_title'] = title  # 拍卖标题
            item['auction_status'] = self.get_status(auction_status)  # 拍卖状态
            # 修复数值字段，确保为空时使用None而不是空字符串
            item['start_price'] = lot_info.get("startPrice")  # 起拍价
            item['price_increase_range'] = lot_info.get("rateLadder")  # 加价幅度
            item['auction_type'] = lot_info.get("auctionType")  # 类型
            item['evaluation_price'] = lot_info.get("assessPrice")  # 评估价
            item['bid_cycle'] = lot_info.get("term")  # 竞价周期
            item['priority_buyer'] = None  # 优先购买人(原数据中未包含此字段)
            item['bond'] = lot_info.get("cashDeposit")  # 保证金
            item['delay_period'] = lot_info.get("delayTime")  # 延迟周期
            item['reserve_price'] = None  # 保留价(原数据中未包含此字段)
            item['subject_matter_location'] = lot_info.get("position")  # 标的所在地
            item['bid_start_time'] = self.convert_timestamp_to_datetime(lot_info.get("startTime", ""))  # 竞价开始时间
            item['bid_end_time'] = self.convert_timestamp_to_datetime(lot_info.get("endTime", ""))  # 竞价结束时间
            company = (
                    lot_info.get("supervisionUnit") or
                    lot_info.get("name") or
                    introduction_info.get("position")
            )
            item['disposal_unit'] = self.extract_company_name(company)  # 处置单位
            item['subject_matter_introduce'] = introduction_info.get("describe")  # 标的物介绍
            # 修复：将图片列表转换为逗号分隔的字符串
            item['subject_matter_img'] = ','.join(jpg_list) if jpg_list else ""  # 标的物图片
            item['subject_matter_attachment'] = ','.join(attachment_list) if attachment_list else ""  # 标的物附件
            item['bid_announcement'] = introduction_info.get("content")  # 竞买公告
            item['bid_notice'] = introduction_info.get("guidance")  # 竞买需知
            item['source_url'] = lot_info.get("source_url")  # 来源
            yield item
