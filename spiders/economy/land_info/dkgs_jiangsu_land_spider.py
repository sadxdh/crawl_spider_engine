"""江苏土地市场网-地块公示 → entity_land_massif_publicity
旧项目参照: data_crawl_server dkgs_jiangsu_land_spider.py
"""
import json, hashlib, scrapy
from datetime import datetime
from spiders.base_spider import BaseSpider
from spiders.economy.land_info.region_code import *
from utils.tools import *


class JiangsuDkgsLandSpider(BaseSpider):
    name = 'economy_jiangsu_dkgs'
    data_table = 'entity_land_massif_publicity'
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
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Origin': 'http://www.landjs.com',
        'Pragma': 'no-cache',
        'Referer': 'http://www.landjs.com/tAfficheParcel/bargainParcelNew',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36 Edg/131.0.0.0',
        'X-Requested-With': 'XMLHttpRequest',
    }

    def start_requests(self):
        json_data = {
            'index': 1,
            'size': 50,
            'keyWordDkbh': '',
            'keyWordLandPosition': '',
            'keyWordAlienee': '',
            'mrFlag': 2,
            'dfTime': 1,
        }
        url = 'http://www.landjs.com/tAfficheParcel/searchBargainParcel'
        yield scrapy.http.JsonRequest(
            url=url,
            method="POST",
            headers=self.headers,
            data=json_data,
            callback=self.get_count_page,
            errback=self.errback,
            dont_filter=True,
        )

    def get_count_page(self, response):
        if self.end_page < 0:
            self.end_page = response.json()['totalPages']
        for page in range(self.start_page, self.end_page + 1):
            json_data = {
                'index': page,
                'size': 50,
                'keyWordDkbh': '',
                'keyWordLandPosition': '',
                'keyWordAlienee': '',
                'mrFlag': 2,
                'dfTime': 1,
            }
            url = 'http://www.landjs.com/tAfficheParcel/searchBargainParcel'
            yield scrapy.http.JsonRequest(
                url=url,
                method="POST",
                headers=self.headers,
                data=json_data,
                callback=self.get_ggid,
                errback=self.errback,
                dont_filter=True,
            )

    def get_ggid(self, response):
        gyggGuid = response.json()['bargainParcelList']
        for date in gyggGuid:
            ggid = date['cjgsGuid']
            release_date = datetime.fromtimestamp(date['bargainDate'] / 1000).strftime('%Y.%m.%d')
            data = {
                'parcelId': f'{ggid}',
                'type': 'bargain',
                'landIds': f'{ggid},',
            }
            headers = {
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Connection": "keep-alive",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Origin": "http://www.landjs.com",
                # "Referer": "http://www.landjs.com/tAfficheParcel/detail/bargain/579d9abf2b2c4491acf2c611be163bef",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
                "X-Requested-With": "XMLHttpRequest",
            }
            data_url = f'http://www.landjs.com/tAfficheParcel/detail/bargain/{ggid}'
            yield scrapy.FormRequest(
                url='http://www.landjs.com/tAfficheParcel/searchParcelInfo',
                method="POST",
                headers=headers,
                formdata=data,
                callback=self.parse_list,
                errback=self.errback,
                dont_filter=True,
                cb_kwargs={'release_date': release_date, 'url': data_url},
            )

    def parse_list(self, response, release_date, url):
        try:
            entry_name = response.json()['tAfficheParcel']['parcelName'] if response.json()[
                'tAfficheParcel'] else ''  # 项目名称
            item = response.json()['tBargainParcel']
            land_parcel_number = item['parcelNo']  # 地块编号
            massif_position = item['landPosition']  # 地块位置
            land_area = item['remiseArea']  # 地块面积
            region = get_region_name(item['xzqDm'])  # 行政区代码
            land_file_title = item['afficheNo']  # 土地文件标题

            transaction_price = item['price']  # 成交价格
            transfer_period = item['useYear']  # 出让年限
            land_use = item['tdYt']  # 土地用途
            transferee = item['alienee']  # 受让单位
            time1 = datetime.fromtimestamp(item['bargainDate'] / 1000).strftime('%Y年%m月%d日') if item[
                'bargainDate'] else ''
            time2 = datetime.fromtimestamp(item['jzrq'] / 1000).strftime('%Y年%m月%d日') if item['jzrq'] else ''
            publicity_period = f'{time1}至{time2}'  # 公示期

            if response.json()['affiche']:
                item = response.json()['affiche']
                units = item['remiseUnit']  # 行政单位
                issuing_authority = item['remiseUnit']  # 发布机关
                contact_unit = item['linkaddress']  # 联系单位
                unit_address = item['linkaddress']  # 单位地址
                contact_phone_number = item['linkphone']  # 联系电话
                contacts = item['linkman']  # 联系人
            else:
                units = issuing_authority = contact_unit = unit_address = contact_phone_number = contacts = ''
            contact_unit = contact_unit.replace('/', '') if contact_unit else ''
            md5_value = hash_md5(land_parcel_number + massif_position)
            items = {}
            items['md5_value'] = md5_value
            items['land_file_title'] = land_file_title
            items['land_parcel_number'] = land_parcel_number
            items['massif_position'] = massif_position
            items['land_area'] = land_area
            items['transaction_price'] = transaction_price
            items['transfer_period'] = transfer_period
            items['land_use'] = land_use
            items['entry_name'] = entry_name
            items['transferee'] = transferee
            items['publicity_period'] = publicity_period
            items['issuing_authority'] = issuing_authority
            items['contact_unit'] = issuing_authority
            items['unit_address'] = unit_address
            items['contact_phone_number'] = contact_phone_number
            items['contacts'] = contacts
            items['details'] = url
            items['release_date'] = release_date
            items['region'] = region
            items['units'] = units
            items['contact_unit'] = contact_unit
            items['source'] = '江苏土地市场网-地块公示'
            # insert_data(table='entity_land_massif_publicity', data=item)
            yield items

        except Exception as e:
            # send_dd_msg(self.spider_name, f'二级url解析失败、数据入库错误，错误：', e)
            self.log_error(f'二级url解析失败、数据入库错误，错误：{e}，url: {url}')

    def errback(self, failure): self.log_error(f'请求失败: {failure.request.url}')
