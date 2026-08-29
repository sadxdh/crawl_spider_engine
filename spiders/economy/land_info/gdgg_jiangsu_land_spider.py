"""江苏土地市场网-供地公告 → entity_land_transfer_announcement
旧项目参照: data_crawl_server gdgg_jiangsu_land_spider.py
"""
import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *
from datetime import datetime
from spiders.economy.land_info.region_code import *

class JiangsuGdggLandSpider(BaseSpider):
    name = 'economy_jiangsu_gdgg'
    data_table = 'entity_land_transfer_announcement'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Origin': 'http://www.landjs.com',
        'Pragma': 'no-cache',
        'Referer': 'http://www.landjs.com/affiche/indexNew/5',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
        'X-Requested-With': 'XMLHttpRequest',
    }

    def start_requests(self):
        json_data = {
            'index': 1,
            'size': 50,
            'mrFlag': 2,
            'keyWordAfficheNo': '',
        }
        url = 'http://www.landjs.com/affiche/information'
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
                'mrFlag': 2,
                'keyWordAfficheNo': '',
            }
            url = 'http://www.landjs.com/affiche/information'
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
        gyggGuid = response.json()['list']
        for date in gyggGuid:
            ggid = date['gyggGuid']
            url = f'http://www.landjs.com/affiche/parcels/{ggid}'

            yield scrapy.Request(
                url=url,
                method="GET",
                headers=self.headers,
                callback=self.get_gid
            )

    def get_gid(self, response):
        title = f"{response.json()['affiche']['afficheName']}{response.json()['affiche']['afficheNo']}"
        releasetime = datetime.fromtimestamp(response.json()['affiche']['afficheDate'] / 1000).strftime(
            '%Y-%m-%d') if response.json()['affiche']['afficheDate'] else ''
        items = response.json()['parcelList']
        for item in items:
            gid = item['ggdkGuid']
            data = {
                'parcelId': gid,
                'type': 'remise',
                'landIds': gid,
            }
            headers = {
                'Accept': '*/*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Origin': 'http://www.landjs.com',
                'Pragma': 'no-cache',
                'Referer': f'http://www.landjs.com/tAfficheParcel/detail/remise/{gid}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
                'X-Requested-With': 'XMLHttpRequest',
            }
            details = f'http://www.landjs.com/tAfficheParcel/detail/remise/{gid}'
            yield scrapy.FormRequest(
                url='http://www.landjs.com/tAfficheParcel/searchParcelInfo',
                headers=headers,
                method='POST',
                formdata=data,
                callback=self.parse_list,
                cb_kwargs={'title': title, 'releasetime': releasetime, 'details': details},
            )

    def parse_list(self, response, title, releasetime, details):
        try:
            item = response.json().get('tAfficheParcel', [])
            if item:
                land_parcel_number = item['parcelNo']  # 地块编号
                elements = item['afficheNo']  # 公告编号
                land_location = item['landPosition']  # 土地位置
                units = item['remiseUnit']  # 行政单位
                transfer_manner = item['remiseType'] + item[
                    'dealType']  # 出让方式
                area = item['remiseArea']  # 出让面积
                transfer_period = item['useYear']  # 出让年限
                minRjl = item['minRjl']
                maxRjl = item['maxRjl']
                floor_area_ratio = f'{minRjl}≤并且≤{maxRjl}'  # 容积率
                minJzMd = item['minJzMd']
                maxJzMd = item['maxJzMd']
                building_density = f'{minJzMd}≤并且≤{maxJzMd}'  # 建筑密度
                minLhl = item['minLhl']
                maxLhl = item['maxLhl']
                greening_rate = f'{minLhl}≤并且≤{maxLhl}'  # 绿化率
                minJzxg = item['minJzxg']
                maxJzxg = item['maxJzxg']
                building_height_limit = f'{minJzxg}≤并且≤{maxJzxg}'  # 建筑限高
                land_use = item['tdYt']  # 土地用途
                starting_price = item['startPrice']  # 起始价
                guarantee_price = item['bail']  # 保证金
                price_increase = item['bidScope']  # 竞价幅度
                bidStarttime = item['bidStarttime'] if item['bidStarttime'] else ''
                bidEndtime = item['bidEndtime'] if item['bidEndtime'] else ''
                # listing_time = f'{bidStarttime}至{bidEndtime}'  # 挂牌时间
                region = get_region_name(item['xzqDm'])
                fjGuids = response.json()['sellFile']
                pdf_url, pdf_name = '', ''
                if fjGuids:
                    for fj in fjGuids:
                        fjGuid = fj['fjGuid']
                        pdf_url = f'http://www.landjs.com/tAfficheParcel/fileDownLoad/{fjGuid}' if fjGuid else ''
                        pdf_name = f'{elements}.pdf'
                md5_value = hash_md5(land_parcel_number + land_location)
                items = {}
                items['md5_value'] = md5_value
                items['details'] = details
                items['land_file_title'] = title
                items['land_location'] = land_location
                items['land_parcel_number'] = land_parcel_number
                items['transfer_manner'] = transfer_manner
                items['region'] = region
                items['units'] = units
                items['area'] = area
                items['transfer_period'] = transfer_period
                items['floor_area_ratio'] = floor_area_ratio
                items['building_density'] = building_density
                items['greening_rate'] = greening_rate
                items['building_height_limit'] = building_height_limit
                items['land_use'] = land_use
                items['starting_price'] = starting_price
                items['guarantee_price'] = guarantee_price
                items['price_increase'] = price_increase
                # item.listing_time = listing_time
                items['listing_start_time'] = bidStarttime
                items['listing_end_time'] = bidEndtime
                items['release_date'] = releasetime
                items['source'] = '江苏土地市场网-供地公告'
                items['elements'] = elements
                items['pdf_url'] = pdf_url
                items['pdf_name'] = pdf_name
                # insert_data(table='entity_land_transfer_announcement', data=item)
                yield items
            else:
                self.log_error(f'错误：网页数据为空，url:{details}')
        except Exception as e:
            self.log_error(f'解析数据失败，错误：{e}，url:{details}')

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url}, 原因: {failure.value}')
