# import hashlib, scrapy
# import re
# import time
# from urllib.parse import urlencode
# from spiders.base_spider import BaseSpider
# from utils.tools import *
# from utils.time_kit import *
#
#
# # 公众号  公安部经侦局
# class PublicSecurityEconomicInvestigationArticleSpider(BaseSpider):
#     name = 'public_security_economic_investigation_article'
#     data_table = 'secret_information'
#     dedup_fields = ['md5_value']
#     custom_settings = {
#         'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
#         'DOWNLOADER_MIDDLEWARES': {
#             'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
#         },
#         # 'COOKIES_ENABLED': True  # 使用cookie字段必须得要
#     }
#     proxy_type = 'long_proxy'
#
#     headers = {
#         "accept": "*/*",
#         "accept-language": "zh-CN,zh;q=0.9",
#         "priority": "u=1, i",
#         # "referer": "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=Mzk0NjU2OTkwNw==&action=getalbum&album_id=3365849116190212098&scene=126&sessionid=1784101501435",
#         "sec-ch-ua": "\"Not;A=Brand\";v=\"8\", \"Chromium\";v=\"150\", \"Google Chrome\";v=\"150\"",
#         "sec-ch-ua-mobile": "?0",
#         "sec-ch-ua-platform": "\"Windows\"",
#         "sec-fetch-dest": "empty",
#         "sec-fetch-mode": "cors",
#         "sec-fetch-site": "same-origin",
#         "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
#         "x-requested-with": "XMLHttpRequest"
#     }
#
#     album_id_list = ['3365849116190212098', '3365857176535203841', '3365863738809024518', '3378735662329495560', '3502073745235787780',
#                      '3502074662144196613', '3733979846968508421', '3502080699140161537', '3585269044523466756', '3954378948254892036']
#
#     begin_msgid_list = {}
#
#     def get_param(self, album_id, begin_msgid, page):
#         params = {
#             "action": "getalbum",
#             "__biz": [
#                 "Mzk0NjU2OTkwNw==",
#                 "Mzk0NjU2OTkwNw=="
#             ],
#             "album_id": album_id,
#             "count": "10",
#             "begin_msgid": begin_msgid,
#             "begin_itemidx": str(page),
#             "uin": "",
#             "key": "",
#             "pass_ticket": "",
#             "wxtoken": "",
#             "devicetype": "",
#             "clientversion": "",
#             "appmsg_token": "",
#             "x5": "0",
#             "f": "json"
#         }
#         return params
#
#     def start_requests(self):
#         for album_id in self.album_id_list:
#             for page in range(self.start_page - 1, self.end_page):
#                 yield from self.get_list(album_id, page)
#
#     def get_list(self, album_id, page):
#         if page == 0:
#             params = self.get_param(album_id, begin_msgid='', page=page)
#         else:
#             params = self.get_param(album_id, begin_msgid=self.begin_msgid_list.get(album_id, ''), page=page)
#         url = "https://mp.weixin.qq.com/mp/appmsgalbum"
#         response = common_request(url=url, headers=self.headers, params=params, proxies_type=True)
#         if response:
#             json_data = response.json()
#             try:
#                 self.begin_msgid_list[album_id] = json_data['getalbum_resp']['article_list'][-1]['msgid']
#                 for data in json_data['getalbum_resp']['article_list']:
#                     title = data['title']
#                     publish_time = self.get_strftime(data['create_time'])
#                     details_url = data['url']
#                     yield scrapy.Request(
#                         url=details_url,
#                         headers=self.headers,
#                         cb_kwargs={'title': title, 'publish_time': publish_time, 'details_url': details_url},
#                         callback=self.parse_details
#                     )
#             except:
#                 self.log_info(album_id)
#                 self.log_info(json_data)
#
#     def get_strftime(self, ts_data):
#         dt = datetime.fromtimestamp(int(ts_data))
#         return dt.strftime("%Y-%m-%d %H:%M:%S")
#
#     def parse_details(self, response, title, publish_time, details_url):
#         content_data = re.findall(r"content_noencode: '(.*?)'", response.text)[0]
#         content_data = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), content_data)
#         content_data = re.sub(r'<img[^>]*?>', '', content_data)     # 去除图片
#
#         data_items = {}
#         data_items["title"] = title
#         data_items["publish_time"] = publish_time
#         data_items["url"] = details_url
#         data_items["content"] = content_data
#         data_items["md5_value"] = hash_md5(f"{details_url}{title}")
#         yield data_items
#
#     def errback(self, failure):
#         self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
