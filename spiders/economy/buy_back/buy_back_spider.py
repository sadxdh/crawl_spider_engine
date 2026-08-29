"""
东方财富股票回购爬虫
数据来源：https://data.eastmoney.com/gphg/hglist.html

增量策略：
  - 列表接口每页50条，按更新时间降序
  - 全量：start_page=1 end_page=20（约1000条）
  - 增量定时：start_page=1 end_page=2（最新100条）
  - 去重字段：md5_value（stock_code + announcement_date 的 md5）

请求链：
  列表接口(RPTA_WEB_GETHGLIST_NEW) → 按 DIM_SCODE 请求详情接口(RPTA_WEB_GETHGDETAIL) → 解析入库

本地调试：
  scrapy crawl economy_east_money_buyback -a start_page=1 -a end_page=2
"""
import hashlib
from datetime import datetime
from urllib.parse import urlencode

import scrapy
from loguru import logger

from spiders.base_spider import BaseSpider
from utils.tools import *


class EastMoneyBuyBackSpider(BaseSpider):
    """东方财富股票回购爬虫"""
    name = 'economy_east_money_buyback'
    data_table = 'entity_buyback'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://data.eastmoney.com/gphg/hglist.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    }
    headers2 = {
        'Host': 'np-cnotice-stock.eastmoney.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    list_url = 'https://datacenter-web.eastmoney.com/api/data/v1/get'

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            params = {
                'callback': '',
                'sortColumns': 'UPD,DIM_DATE,DIM_SCODE',
                'sortTypes': '-1,-1,-1',
                'pageSize': '50',
                'pageNumber': page,
                'reportName': 'RPTA_WEB_GETHGLIST_NEW',
                'columns': 'ALL',
                'source': 'WEB',
            }
            separator = '&' if '?' in self.list_url else '?'
            request_url = f'{self.list_url}{separator}{urlencode(params)}'

            yield scrapy.Request(
                url=request_url,
                method='GET',
                headers=self.headers,
                callback=self.parse_buyback_list,
                dont_filter=True,
            )

    def parse_buyback_list(self, response):
        result = response.json()['result']['data']
        for res in result:
            security_code = res['DIM_SCODE']
            detail_url = ('https://datacenter-web.eastmoney.com/api/data/v1/get?callback='
                          '&reportName=RPTA_WEB_GETHGDETAIL&columns=ALL&sortColumns=DIM_DATE&sortTypes=-1'
                          f'&source=WEB&filter=(DIM_SCODE%3D%22{security_code}%22)')
            yield scrapy.Request(
                url=detail_url,
                headers=self.headers,
                callback=self.parse_detail
            )

    def parse_detail(self, response):
        details_result = response.json()['result']['data']
        for details_data in details_result:
            stock_code = details_data.get('DIM_SCODE')  # stock_code  股票代码
            stock_name = details_data.get('SECURITYSHORTNAME')  # entity_name	公司名称
            latest_closing_price = details_data.get('NEWPRICE')  # 最新收盘价
            previous_closing_price = details_data.get('CPRICE')  # 公告前一日收盘价
            planned_price_ceiling = details_data.get('REPURPRICECAP')  # 计划回购价格上限(元)
            lower_bound_of_planned_price = details_data.get('REPURPRICELOWER')  # 计划回购价格下限(元)
            plan_repurchase_shares_amount = details_data.get('REPURNUMCAP')  # 计划回购股份数额  上限
            lower_limit_planned_quantity = details_data.get('REPURNUMLOWER')  # 计划回购数量下限(股)
            lower_limit_planned_amount = details_data.get('REPURAMOUNTLOWER')  # 计划回购金额下限(元)
            upper_limit_planned_amount = details_data.get('REPURAMOUNTLIMIT')  # 计划回购金额上限(元)
            announcement_date = details_data.get('DIM_DATE')  # announcement_date	公告日期
            share_type = details_data.get('SHARETYPE')  # 回购股份类型
            objective = details_data.get('REPUROBJECTIVE')  # 回购目的
            hot_tip = details_data.get('REMARK')  # 特别提示
            state_update = details_data.get('UPDATEDATE')  # 状态更新时间
            repurchase_time = details_data.get('REPURSTARTDATE')  # repurchase_time	回购时间
            repurchase_deadline = details_data.get('REPURENDDATE')  # repurchase_deadline	回购截止日期
            repurchased_lower_limit = details_data.get('REPURPRICELOWER1')  # 已回购股份价格下限(元)
            repurchased_upper_limit = details_data.get('REPURPRICECAP1')  # 已回购股份价格上限(元)
            repurchased_shares = details_data.get('REPURNUM')  # 已回购股份数量(股)
            repurchased_amount = details_data.get('REPURAMOUNT')  # 已回购金额(元)
            repurchase_price = details_data.get('REPURPRICECAP')  # repurchase_price	回购价格(万元)

            detail_date = announcement_date.split(' ')[0]
            details = f'https://data.eastmoney.com/gphg/detail/{stock_code}-{detail_date}.html'
            md5_value = hash_md5(stock_code + announcement_date)

            items = {}
            items['md5_value'] = md5_value
            items['stock_code'] = stock_code
            items['stock_name'] = stock_name
            items['latest_closing_price'] = latest_closing_price
            items['previous_closing_price'] = previous_closing_price
            items['planned_price_ceiling'] = planned_price_ceiling
            items['lower_bound_of_planned_price'] = lower_bound_of_planned_price
            items['plan_repurchase_shares_amount'] = plan_repurchase_shares_amount
            items['lower_limit_planned_quantity'] = lower_limit_planned_quantity
            items['lower_limit_planned_amount'] = lower_limit_planned_amount
            items['upper_limit_planned_amount'] = upper_limit_planned_amount
            items['announcement_date'] = announcement_date
            items['share_type'] = share_type
            items['objective'] = objective
            items['hot_tip'] = hot_tip
            items['state_update'] = state_update
            items['repurchase_time'] = repurchase_time
            items['repurchase_deadline'] = repurchase_deadline
            items['repurchased_lower_limit'] = repurchased_lower_limit
            items['repurchased_upper_limit'] = repurchased_upper_limit
            items['repurchased_shares'] = repurchased_shares
            items['repurchased_amount'] = repurchased_amount
            items['details'] = details
            items['repurchase_price'] = repurchase_price
            # insert_data(table='entity_buyback', data=item)
            yield items
            # yield from self.download_file({'stock_code': stock_code, 'md5_value': md5_value, 'items': items})

    # def download_file(self, data):
    #     # 抓取回购公告文件 按股票代码搜索
    #     stock_code = data['stock_code']
    #     md5_value = data['md5_value']
    #     url = (
    #         'https://np-anotice-stock.eastmoney.com/api/security/ann?cb=&sr=-1&page_size=50&page_index=1&ann_type=A'
    #         f'&client_source=web&stock_list={stock_code}&f_node=0&s_node=0')
    #     yield scrapy.Request(
    #         url=url,
    #         headers=self.headers,
    #         callback=self.parse_file,
    #         cb_kwargs={'md5_value': md5_value, 'items': data['items']}
    #     )
    #
    # def parse_file(self, response, md5_value, items):
    #     result = response.json()['data']['list']
    #     for data in result:
    #         art_code = data['art_code']
    #         art_title = data['title']
    #         if '回购' in art_title:
    #             get_pdffile_url = (f'https://np-cnotice-stock.eastmoney.com/api/content/ann?cb=&art_code={art_code}'
    #                                '&client_source=web&page_index=1')
    #             yield scrapy.Request(
    #                 url=get_pdffile_url,
    #                 headers=self.headers2,
    #                 callback=self.parse_file_data,
    #                 cb_kwargs={'md5_value': md5_value, 'art_title': art_title, 'items': items}
    #             )
    #             break
    # def parse_file_data(self, response, md5_value, art_title, items):
    #     get_pdffile_responses_json = response.json()
    #     pdffile_url = get_pdffile_responses_json['data']['attach_list'][0]['attach_url']
    #     # items = {}
    #     items['announcement_title'] = art_title
    #     items['announcement_url'] = pdffile_url
    #     # items['md5_value'] = md5_value
    #     # update_data(table_name='entity_buyback', data=temp)
    #     # self.log_info(items)
    #     yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} - {failure.value}')
