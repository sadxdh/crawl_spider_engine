# # 豌豆荚获取安卓app更新日志
# from scrapy import Request, FormRequest
# from utils.tools import *
# from spiders.base_spider import BaseSpider
# from utils.mysql_tools import select_data, update_set
#
#
# class WanDouJiaSpider(BaseSpider):
#     name = 'company_app_wdj'
#     data_table = 'layout_design'
#     custom_settings = {
#         'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
#         'DOWNLOADER_MIDDLEWARES': {
#             'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
#         }
#     }
#     proxy_type = 'long_proxy'
#     headers = {
#         'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,'
#                   '*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
#         'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
#         'referer': 'https://www.wandoujia.com/',
#     }
#
#
#     def start_requests(self):
#         num = int(self.end_page) - int(self.start_page)
#         data = ['app_name', 'developer', 'md5_value']
#         condition = f'where log is null and platform="android" limit {num} offset {self.start_page}'
#         datas = select_data(
#             table='app_info',
#             data=data,
#             condition=condition
#         )
#
#         for data in datas:
#             self.logger.info(data)
#             app_name = data.get('app_name')
#             params = {
#                 'key': app_name,
#                 'source': 'index',
#             }
#
#             yield FormRequest(
#                 url='https://www.wandoujia.com/search',
#                 method='GET',
#                 formdata=params,
#                 meta={'data': data},
#                 headers=self.headers,
#                 callback=self.parse,
#                 dont_filter=True,
#             )
#
#     def parse(self, response, *args):
#         meta = response.meta
#         data = meta['data']
#
#         url = None
#         rows = response.xpath('//ul[@id="j-search-list"]/li')
#         for row in rows:
#             app_title = row.xpath('./div[@class="app-desc"]/h2/a/text()').get()
#             app_url = row.xpath('./div[@class="app-desc"]/h2/a/@href').get()
#             if app_title == data['app_name']:
#                 url = app_url
#                 break
#
#         if url:
#             yield Request(
#                 url=url,
#                 headers=self.headers,
#                 meta={'data': data},
#                 callback=self.parse_detail,
#                 dont_filter=True,
#             )
#         else:
#             self.logger.warning(f'未找到软件:{data.get("app_name")}')
#             update_set(
#                 table='app_info',
#                 data={'log': 0},
#                 condition=f'md5_value="{data["md5_value"]}"'
#             )
#
#     def parse_detail(self, response):
#         meta = response.meta
#         data = meta['data']
#
#         history_log_url = response.xpath('//div[@id="allVersion"]/h2/a/@href').get()
#         dev = response.xpath('//dt[contains(text(),"开发者")]/following-sibling::dd[1]/span/text()').get()
#         if dev and history_log_url:
#             yield Request(
#                 url=history_log_url,
#                 headers=self.headers,
#                 meta={'data': data},
#                 callback=self.parse_log_list,
#                 dont_filter=True,
#             )
#
#     async def parse_log_list(self, response):
#         meta = response.meta
#         data = meta['data']
#         md5_value = data['md5_value']
#
#         headers = {
#             'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
#             'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
#             'referer': 'https://www.wandoujia.com/apps/28047/history',
#             'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0',
#         }
#
#         log_list = []
#         rows = response.xpath('//div[@class="all-version"]/ul/li')
#         for row in rows:
#             img = row.xpath('./a/div/img/@src').get()
#             log_detail_url = row.xpath('./a[(div)]/@href').get()
#
#
#             proxy = ScrapyProxy.get_long_proxy()
#             result = await make_async_request(
#                 url=log_detail_url,
#                 headers=headers,
#                 method='GET',
#                 proxy=proxy,
#                 ssl=False
#             )
#             if not result:
#                 continue
#             result = etree.HTML(result.decode('utf-8'))
#
#             app_name = xpath_parse(result, '//p[@class="app-name"]/span/text()')
#             app_version = xpath_parse(result, '//p[@class="version-name"]/span//text()')
#             update_time = xpath_parse(result, '//p[@class="update-time"]/text()')
#             log = xpath_parse(result, '//div[@class="history-desc"]/div/div[1]//text()')
#
#             update_time = update_time.split('：')[1] if update_time else None
#             log = log.strip() if log else None
#
#             temp = {
#                 'app_name': app_name,
#                 'app_icon': img,
#                 'app_version': app_version,
#                 'update_time': update_time,
#                 'log': log,
#             }
#             self.logger.info(f'更新日志解析结果: {temp}')
#             log_list.append(temp)
#
#         logs = json.dumps(log_list, ensure_ascii=False)
#         update_set(
#             table='app_info',
#             data={'log': logs},
#             condition=f'md5_value="{md5_value}"'
#         )
#
