"""江苏土地市场网-供地结果 → entity_land_contract_signing
旧项目参照: data_crawl_server gdjg_jiangsu_land_spider.py
"""
import scrapy
from datetime import datetime
from spiders.base_spider import BaseSpider
from utils.tools import *
from spiders.economy.land_info.region_code import *


class JiangsuGdjgLandSpider(BaseSpider):
    name = 'economy_jiangsu_gdjg'
    data_table = 'entity_land_contract_signing'
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
        'Content-Type': 'application/Json',
        'Origin': 'http://www.landjs.com',
        'Pragma': 'no-cache',
        'Referer': 'http://www.landjs.com/tAfficheParcel/bulletinNew',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36 Edg/131.0.0.0',
        'X-Requested-With': 'XMLHttpRequest',
    }

    @staticmethod
    def get_date(date):
        return datetime.fromtimestamp(date / 1000).strftime('%Y-%m-%d') if date else ''

    @staticmethod
    def get_tddj(dj):
        tdjb_dict = {
            "dj1": "一级",
            "dj2": "二级",
            "dj3": "三级",
            "dj4": "四级",
            "dj5": "五级",
            "dj6": "六级",
            "dj7": "七级",
            "dj8": "八级",
            "dj9": "九级",
            "dj10": "十级",
            "dj11": "十一级",
            "dj12": "十二级",
            "dj13": "十三等级",
            "dj14": "十四等级",
            "dj15": "十五等级",
            "dj16": "十六等级",
            "dj17": "十七等级",
            "dj18": "十八等级",
            "dj0": "未评估地区"
        }
        return tdjb_dict.get(dj)

    @staticmethod
    def ensure_str(value):
        """ 确保值是字符串格式，如果为 None 或其他非字符串值，则转换为空字符串 """
        if value is None:
            return ''
        return str(value).replace('None', '')

    def start_requests(self):
        json_data = {
            "index": 1,
            "size": 50,
            "keyWordXmmc": "",
            "keyWordLandUser": "",
            "keyWordTdZl": "",
            "keyWordBh": "",
            "keyWordDzBaBh": "",
            "mrFlag": 3
        }
        url = 'http://www.landjs.com/tAfficheParcel/bulletinInfo'
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
                "index": page,
                "size": 50,
                "keyWordXmmc": "",
                "keyWordLandUser": "",
                "keyWordTdZl": "",
                "keyWordBh": "",
                "keyWordDzBaBh": "",
                "mrFlag": 3
            }
            url = 'http://www.landjs.com/tAfficheParcel/bulletinInfo'
            yield scrapy.http.JsonRequest(
                url=url,
                method="POST",
                headers=self.headers,
                data=json_data,
                callback=self.get_gdGuid,
                errback=self.errback,
                dont_filter=True,
            )

    def get_gdGuid(self, response):
        gdGuid_list = response.json()['list']
        for date in gdGuid_list:
            gdGuid = date['gdGuid']
            cookies = {
                'server': '6EE8D8F804150BB0E17B9488E58FAE6B',
            }
            headers = {
                'Accept': '*/*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Origin': 'http://www.landjs.com',
                'Pragma': 'no-cache',
                'Referer': f'http://www.landjs.com/tAfficheParcel/detail/gdxm/{gdGuid}',
                'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36 Edg/131.0.0.0',
                'X-Requested-With': 'XMLHttpRequest',
            }
            data = {
                'parcelId': gdGuid,
                'type': 'gdxm',
                'landIds': f'{gdGuid},',
            }
            details = f'http://www.landjs.com/tAfficheParcel/detail/gdxm/{gdGuid}'

            yield scrapy.FormRequest(
                url='http://www.landjs.com/tAfficheParcel/searchParcelInfo',
                method='POST',
                headers=headers,
                formdata=data,
                callback=self.parse_list,
                errback=self.errback,
                dont_filter=True,
                cb_kwargs={'details': details}
            )

    def parse_list(self, response, details):

        try:
            item1 = response.json().get('tGdxm', {})
            item2 = response.json().get('tBargainParcel', None) or {}
            if not item1 and not item2:
                self.log_error(f'二级url解析失败，错误：页面数据为空,url: {details}')
            entry_name = self.ensure_str(item1.get('xmMc'))
            project_location = self.ensure_str(item1.get('tdZl'))
            administrative_region = self.ensure_str(get_region_name(item1.get('xzqDm')))
            electronic_supervision_number = self.ensure_str(item1.get('dzBaBh'))
            area = self.ensure_str(item1.get('gdZmj'))
            land_use_period = self.ensure_str(item1.get('crNx'))
            land_level = self.ensure_str(self.get_tddj(item1.get('tdJb')))
            transaction_price = self.ensure_str(item1.get('cjPrice'))
            land_use_rights_holder = self.ensure_str(item1.get('landUser'))
            approval_unit = self.ensure_str(item1.get('pzJg'))
            contract_signing_date = self.ensure_str(self.get_date(item1.get('qdRq')))
            agreed_delivery_date = self.ensure_str(self.get_date(item1.get('jdSj')))
            agreed_commencement_time = self.ensure_str(self.get_date(item1.get('dgSj')))
            agreed_completion_time = self.ensure_str(self.get_date(item1.get('jgSj')))
            agreed_lower_limit = self.ensure_str(item1.get('minRjl'))
            agreed_upper_limit = self.ensure_str(item1.get('maxRjl'))

            land_use = self.ensure_str(item2.get('tdYt'))
            land_supply_method = f"{item2.get('remiseType')}{item2.get('dealType')}"
            land_supply_method = self.ensure_str(land_supply_method)
            industry_classification = self.ensure_str(item2.get('landUse'))

            md5_value = hash_md5(entry_name + project_location)
            items = {}
            items['md5_value'] = md5_value
            items['administrative_region'] = administrative_region
            items['electronic_supervision_number'] = electronic_supervision_number
            items['entry_name'] = entry_name
            items['project_location'] = project_location
            items['area'] = area
            items['land_use'] = land_use
            items['land_supply_method'] = land_supply_method
            items['land_use_period'] = land_use_period
            items['industry_classification'] = industry_classification
            items['land_level'] = land_level
            items['transaction_price'] = transaction_price
            items['land_use_rights_holder'] = land_use_rights_holder
            items['approval_unit'] = approval_unit
            items['contract_signing_date'] = contract_signing_date
            items['agreed_delivery_date'] = agreed_delivery_date
            items['agreed_commencement_time'] = agreed_commencement_time
            items['agreed_completion_time'] = agreed_completion_time
            items['agreed_lower_limit'] = agreed_lower_limit
            items['agreed_upper_limit'] = agreed_upper_limit
            items['details'] = details
            items['land_source'] = '江苏土地市场网-供地结果'
            # insert_data(table='entity_land_contract_signing', data=item)
            yield items
        except Exception as e:
            # send_dd_msg(self.spider_name, f'二级url解析失败、数据入库错误，错误：', e)
            self.log_error(f'二级url解析失败、数据入库错误，错误：{e},url: {details}')

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
