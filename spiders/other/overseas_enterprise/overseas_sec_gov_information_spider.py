# import hashlib, scrapy
# from urllib.parse import urlencode
# from spiders.base_spider import BaseSpider
# from utils.tools import *
# from utils.time_kit import *
#
# class OverseasSecGovInformationSpider(BaseSpider):
#     name = 'overseas_sec_gov_information'
#     data_table = ''
#     dedup_fields = ['md5_value']
#     custom_settings = {
#         'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
#         'DOWNLOADER_MIDDLEWARES': {
#             'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
#         },
#         #'COOKIES_ENABLED': True  # 使用cookie字段必须得要
#     }
#     proxy_type = 'long_proxy'
#
#     headers = {
#         "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
#         "accept-language": "zh-CN,zh;q=0.9",
#         "cache-control": "max-age=0",
#         "if-modified-since": "Wed, 15 Jul 2026 20:47:26 GMT",
#         "priority": "u=0, i",
#         "sec-ch-ua": "\"Not;A=Brand\";v=\"8\", \"Chromium\";v=\"150\", \"Google Chrome\";v=\"150\"",
#         "sec-ch-ua-mobile": "?0",
#         "sec-ch-ua-platform": "\"Windows\"",
#         "sec-fetch-dest": "document",
#         "sec-fetch-mode": "navigate",
#         "sec-fetch-site": "none",
#         "sec-fetch-user": "?1",
#         "upgrade-insecure-requests": "1",
#         "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
#     }
#
#     def start_requests(self):
#         all_info_url = 'https://www.sec.gov/files/company_tickers.json'
#         yield scrapy.Request(
#             url=all_info_url,
#             headers=self.headers,
#             callback=self.parse_list
#         )
#
#     def parse_list(self, response):
#         json_data = response.json()
#         for index, info_data in json_data.items():
#             cik_str = str(info_data["cik_str"]).zfill(10)
#             req_url = f"https://data.sec.gov/submissions/CIK{cik_str}.json"
#             yield scrapy.Request(
#                 url=req_url,
#                 headers=self.headers,
#                 callback=self.parse_details
#             )
#
#     def fmt_address(self, addr):
#         """把地址字典拼成一行可读字符串"""
#         if not addr:
#             return ""
#         parts = [
#             addr.get("street1"),
#             addr.get("street2"),
#             addr.get("city"),
#             addr.get("stateOrCountryDescription") or addr.get("stateOrCountry"),
#             addr.get("zipCode"),
#             addr.get("country"),
#         ]
#         return ", ".join(p for p in parts if p)
#
#     def parse_details(self, response):
#         data_list = response.json()
#
#         addresses = data_list.get("addresses", {}) or {}
#         business_addr = addresses.get("business", {}) or {}
#         mailing_addr = addresses.get("mailing", {}) or {}
#         former_names = data_list.get("formerNames", []) or []
#
#         data_items = {}
#         data_items['cik'] = data_list.get('cik')  # SEC 中央索引码 CIK
#         data_items['company_name'] = data_list.get('name')  # 企业名称
#         data_items['entity_type'] = data_list.get('entityType')  # 实体类型
#         data_items['sic'] = data_list.get('sic')  # 标准行业分类代码
#         data_items['sic_description'] = data_list.get('sicDescription')  # 行业分类描述
#         data_items['owner_org'] = data_list.get('ownerOrg')  # 所属组织/部门
#         data_items['ein'] = data_list.get('ein')  # 雇主识别号(税号)
#         data_items['lei'] = data_list.get('lei')  # 法人机构识别编码
#         data_items['tickers'] = data_list.get('tickers')  # 股票代码
#         data_items['exchanges'] = data_list.get('exchanges')  # 上市交易所
#         data_items['category'] = data_list.get('category')  # 申报人类别
#         data_items['fiscal_year_end'] = data_list.get('fiscalYearEnd')  # 财年结束日(MMDD)
#         data_items['state_of_incorporation'] = data_list.get('stateOfIncorporation')  # 注册地(州代码)
#         data_items['state_of_incorporation_desc'] = data_list.get('stateOfIncorporationDescription')  # 注册地描述
#         data_items['description'] = data_list.get('description')  # 描述
#         data_items['website'] = data_list.get('website')  # 官网
#         data_items['investor_website'] = data_list.get('investorWebsite')  # 投资者关系网站
#         data_items['phone'] = data_list.get('phone')  # 联系电话
#         data_items['flags'] = data_list.get('flags')  # 标记
#
#         # 联系地址
#         data_items['business_address'] = self.fmt_address(business_addr)  # 办公地址
#         data_items['business_street1'] = business_addr.get('street1')  # 办公地址-街道1
#         data_items['business_street2'] = business_addr.get('street2')  # 办公地址-街道2
#         data_items['business_city'] = business_addr.get('city')  # 办公地址-城市
#         data_items['business_state'] = business_addr.get('stateOrCountryDescription')  # 办公地址-州/国家
#         data_items['business_zip'] = business_addr.get('zipCode')  # 办公地址-邮编
#
#         data_items['mailing_address'] = self.fmt_address(mailing_addr)  # 邮寄地址
#         data_items['mailing_street1'] = mailing_addr.get('street1')  # 邮寄地址-街道1
#         data_items['mailing_street2'] = mailing_addr.get('street2')  # 邮寄地址-街道2
#         data_items['mailing_city'] = mailing_addr.get('city')  # 邮寄地址-城市
#         data_items['mailing_state'] = mailing_addr.get('stateOrCountryDescription')  # 邮寄地址-州/国家
#         data_items['mailing_zip'] = mailing_addr.get('zipCode')  # 邮寄地址-邮编
#
#         # 曾用名
#         data_items['former_names'] = [fn.get('name') for fn in former_names]  # 曾用名列表
#         data_items['former_names_detail'] = [  # 曾用名(含启用/停用时间)
#             {
#                 'name': fn.get('name'),
#                 'from': fn.get('from'),
#                 'to': fn.get('to'),
#             }
#             for fn in former_names
#         ]
#
#         # 内部人交易标记
#         data_items['insider_txn_for_owner'] = data_list.get('insiderTransactionForOwnerExists')  # 是否存在所有者内部交易
#         data_items['insider_txn_for_issuer'] = data_list.get('insiderTransactionForIssuerExists')  # 是否存在发行方内部交易
#
#
#
#
#     def errback(self, failure):
#         self.log_error(f'请求失败: {failure.request.url} — {failure.value}')