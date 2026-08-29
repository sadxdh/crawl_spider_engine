# import hashlib, scrapy
# from urllib.parse import urlencode
# from spiders.base_spider import BaseSpider
# from utils.tools import *
# from utils.time_kit import *
#
# class OverseasLeiInformationSpider(BaseSpider):
#     name = 'overseas_lei_information'
#     data_table = 'lei_company_info'
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
#         "accept": "application/json, text/plain, */*",
#         "accept-language": "zh-CN,zh;q=0.9",
#         "origin": "https://search.gleif.org",
#         "priority": "u=1, i",
#         "referer": "https://search.gleif.org/",
#         "sec-ch-ua": "\"Not;A=Brand\";v=\"8\", \"Chromium\";v=\"150\", \"Google Chrome\";v=\"150\"",
#         "sec-ch-ua-mobile": "?0",
#         "sec-ch-ua-platform": "\"Windows\"",
#         "sec-fetch-dest": "empty",
#         "sec-fetch-mode": "cors",
#         "sec-fetch-site": "same-site",
#         "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
#     }
#
#     def start_requests(self):
#         for page in range(self.start_page, self.end_page + 1):
#             params = {
#                 "page[number]": page,
#                 "page[size]": 15,
#             }
#             url = f'{"https://api.gleif.org/api/v1/lei-records?"}{urlencode(params)}'
#
#             yield scrapy.Request(
#                 url=url,
#                 headers=self.headers,
#                 callback=self.parse_list,
#             )
#
#     def to_mysql_datetime(self, value):
#         """把 ISO 格式(如 2022-06-02T00:00:00Z)转成 MySQL DATETIME(2022-06-02 00:00:00)。"""
#         if not value:
#             return None
#         # 去掉末尾的 Z，把 T 换成空格；同时兼容带时区偏移(如 +00:00)的情况
#         s = value.replace("Z", "").replace("T", " ")
#         # 若含时区偏移，截断到秒
#         if "+" in s:
#             s = s.split("+")[0]
#         return s.strip()
#
#     def get_data(self, d, *keys, default=None):
#         """安全地按层级取值，任意一层缺失就返回 default。"""
#         for k in keys:
#             if not isinstance(d, dict):
#                 return default
#             d = d.get(k)
#             if d is None:
#                 return default
#         return d
#
#     def format_address(self, addr):
#         """把地址对象拼成一行可读字符串。"""
#         if not isinstance(addr, dict):
#             return None
#         parts = []
#         lines = addr.get("addressLines") or []
#         parts.extend(lines)
#         for key in ("postalCode", "city", "region", "country"):
#             val = addr.get(key)
#             if val:
#                 parts.append(val)
#         return ", ".join(parts) if parts else None
#
#     def parse_lei_record(self, record):
#         """从单条 lei-records 里抽取尽可能详细的工商信息。"""
#         attr = record.get("attributes", {})
#         entity = attr.get("entity", {})
#         registration = attr.get("registration", {})
#
#         data_items = {}
#
#         # ---------- 基本标识 ----------
#         lei = record.get("id")
#         data_items["lei"] = lei  # LEI 法人识别编码
#
#         # 企业详情链接
#         detail_url = f"https://search.gleif.org/#/record/{lei}"
#         data_items["detail_url"] = detail_url  # 企业详情链接
#
#         data_items["md5_value"] = hash_md5(detail_url)
#
#         data_items["company_name"] = self.get_data(entity, "legalName", "name")  # 企业法定名称
#         data_items["company_name_lang"] = self.get_data(entity, "legalName", "language")  # 名称语言
#
#         # ---------- 曾用名 / 其他名称 ----------
#         other_names = entity.get("otherNames") or []
#         data_items["previous_names"] = [
#             n.get("name") for n in other_names if n.get("type") == "PREVIOUS_LEGAL_NAME"
#         ]  # 曾用名列表
#         data_items["other_names"] = [n.get("name") for n in other_names]  # 全部其他名称
#
#         # ---------- 地址 ----------
#         data_items["legal_address"] = self.format_address(entity.get("legalAddress"))  # 注册地址
#         data_items["headquarters_address"] = self.format_address(entity.get("headquartersAddress"))  # 总部地址
#         data_items["city"] = self.get_data(entity, "legalAddress", "city")  # 城市
#         data_items["region"] = self.get_data(entity, "legalAddress", "region")  # 地区/州省
#         data_items["country"] = self.get_data(entity, "legalAddress", "country")  # 国家
#         data_items["postal_code"] = self.get_data(entity, "legalAddress", "postalCode")  # 邮编
#
#         # ---------- 工商登记信息 ----------
#         data_items["registration_number"] = entity.get("registeredAs")  # 工商登记号 (如 HRB 286801)
#         data_items["registered_authority"] = self.get_data(entity, "registeredAt", "id")  # 登记机构代码
#         data_items["jurisdiction"] = entity.get("jurisdiction")  # 法律管辖区
#         data_items["category"] = entity.get("category")  # 实体类别
#         data_items["legal_form"] = self.get_data(entity, "legalForm", "id")  # 法律形式代码 (如 GmbH=2HBR)
#         data_items["entity_status"] = entity.get("status")  # 实体状态 ACTIVE/INACTIVE
#         data_items["creation_date"] = self.to_mysql_datetime(entity.get("creationDate") ) # 公司成立日期
#
#         # ---------- 消亡 / 继承 ----------
#         data_items["expiration_date"] = self.to_mysql_datetime(self.get_data(entity, "expiration", "date"))  # 消亡日期
#         data_items["expiration_reason"] = self.get_data(entity, "expiration", "reason")  # 消亡原因
#         data_items["successor_lei"] = self.get_data(entity, "successorEntity", "lei")  # 继承实体 LEI
#
#         # ---------- 事件（改名/合并等）----------
#         events = []
#         for grp in entity.get("eventGroups") or []:
#             for ev in grp.get("events") or []:
#                 events.append({
#                     "type": ev.get("type"),  # 事件类型 如 CHANGE_LEGAL_NAME
#                     "status": ev.get("status"),  # 状态 COMPLETED
#                     "effective_date": ev.get("effectiveDate"),  # 生效日
#                     "recorded_date": ev.get("recordedDate"),  # 记录日
#                 })
#         data_items["events"] = events
#
#         # ---------- LEI 注册/维护信息 ----------
#         data_items["lei_status"] = registration.get("status")  # LEI 状态 ISSUED/LAPSED
#         data_items["initial_registration_date"] = self.to_mysql_datetime(registration.get("initialRegistrationDate"))  # 首次注册
#         data_items["last_update_date"] = self.to_mysql_datetime(registration.get("lastUpdateDate"))  # 最近更新
#         data_items["next_renewal_date"] = self.to_mysql_datetime(registration.get("nextRenewalDate"))  # 下次续期截止
#         data_items["managing_lou"] = registration.get("managingLou")  # 管理机构 LOU
#         data_items["corroboration_level"] = registration.get("corroborationLevel")  # 数据核实等级
#         data_items["validated_as"] = registration.get("validatedAs")  # 核实用登记号
#
#         # ---------- 其他关联标识符 ----------
#         data_items["bic"] = attr.get("bic")  # 银行 BIC/SWIFT
#         data_items["mic"] = attr.get("mic")  # 交易所市场识别码
#         data_items["isin_count"] = attr.get("spglobal")
#
#         return data_items
#
#     def parse_list(self, response):
#         json_data = response.json()
#         for data_list in json_data['data']:
#             data_data = self.parse_lei_record(data_list)
#             yield data_data
#
#
#     def errback(self, failure):
#         self.log_error(f'请求失败: {failure.request.url} — {failure.value}')