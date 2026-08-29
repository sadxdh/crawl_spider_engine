"""建材物料 → material_info
参照旧项目 data_crawl_server CneptpMaterialSpider:
  cneptp.com API → 分类→列表→详情→入库
Token: xj-token(临时,可过期) ← zToken(永久用户凭证) 刷新
"""
import json
import requests
import scrapy

from spiders.base_spider import BaseSpider
from utils.db.redis_opt import hgetall
from utils.tools import *
import math
from spiders.economy.material_economy.geetest_verify import cneptp_login


class MaterialCneptpSpider(BaseSpider):
    name = 'economy_material_cneptp'
    data_table = 'material_info'

    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 1, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        },
        'COOKIES_ENABLED': True  # 使用cookie字段必须得要
    }
    proxy_type = 'long_proxy'

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://www.cneptp.com",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "sec-ch-ua": "\"Chromium\";v=\"146\", \"Not-A.Brand\";v=\"24\", \"Google Chrome\";v=\"146\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
    }

    login_cookie = {
        'xj-token': ''
    }

    ztoken_cookies = {
        "zToken": '',
    }

    cookie_status = True

    cneptplogin = cneptp_login()

    def get_cookies(self):
        cookies_dict = hgetall(self.cneptplogin.COOKIE_REDIS_KEY)
        self.log_info(cookies_dict)
        if self.cookie_status:
            mobile, cookies = random.choice(list(cookies_dict.items()))
            self.ztoken_cookies['zToken'] = json.loads(cookies.decode('utf-8')).get('zToken')
            self.updata_cookie()
        else:
            ztoken_cookies = self.cneptplogin.get_login()
            self.ztoken_cookies['zToken'] = ztoken_cookies['zToken']
            self.updata_cookie()
            self.cookie_status = True

    def updata_cookie(self):

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://account.cneptp.com",
            "Pragma": "no-cache",
            "Referer": "https://account.cneptp.com/verify?appKey=782b259830834cdcbe61c51c9a73e889&redirect=https%3A%2F%2Fwww.cneptp.com%2Findex",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            "sec-ch-ua": "\"Chromium\";v=\"146\", \"Not-A.Brand\";v=\"24\", \"Google Chrome\";v=\"146\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
        }
        url = "https://account.cneptp.com/prod-api/passport/user/client/token/check"
        data = {
            "redirect": "https://www.cneptp.com/index",
            "serverType": 2,
            "appKey": "782b259830834cdcbe61c51c9a73e889"
        }
        data = json.dumps(data, separators=(',', ':'))
        response1 = requests.post(url, headers=headers, cookies=self.ztoken_cookies, data=data)
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Referer": "https://account.cneptp.com/verify?appKey=782b259830834cdcbe61c51c9a73e889&redirect=https%3A%2F%2Fwww.cneptp.com%2Findex",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            "sec-ch-ua": "\"Chromium\";v=\"146\", \"Not-A.Brand\";v=\"24\", \"Google Chrome\";v=\"146\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\""
        }
        try:
            url = "https://account.cneptp.com/prod-api/passport/index"
            params = {
                "uuid": response1.json()['data']['uuid'],
                "redirect": "https://www.cneptp.com/index",
                "keepLogin": "1",
                "appKey": "782b259830834cdcbe61c51c9a73e889"
            }
            response2 = requests.get(url, headers=headers, cookies=response1.cookies, params=params, allow_redirects=False)
            response3 = requests.get(response2.headers['Location'], headers=headers, cookies=response1.cookies,
                                     params=params, allow_redirects=False)
            self.login_cookie["xj-token"] = response3.cookies["xj-token"]
            self.log_info(f'spider_name: {self.name} Crawling  cookie更新成功')
        except:
            self.log_info(f'spider_name: {self.name} Crawling  cookie更新失败')
            self.cookie_status = False
            self.get_cookies()

    def get_material(self):
        time.sleep(random.uniform(2, 5))
        url = "https://www.cneptp.com/prod-api/zzyc_public/api/price/home/query/category/crumbs"
        data = {
            "goodsType": 1
        }
        data = json.dumps(data, separators=(',', ':'))
        response = common_request(url, headers=self.headers, data=data, method='POST', proxies_type=True)
        try:
            return response.json()['data'][0]['dataList']
        except Exception as e:
            error_msg = f'材料级别分类, 列表解析错误: {e}'
            self.log_info(error_msg)
            return []

    def get_page_num(self, material):
        time.sleep(random.uniform(3, 6))
        url = "https://www.cneptp.com/prod-api/zzyc_public/api/goods/price/search"
        data = {
            "pageNum": 1,
            "pageSize": 20,
            "keyword": "",
            "propList": [],
            "type": 1,
            "categoryList": [
                {
                    "categoryId": material['material_third_id']
                }
            ],
            "sortKey": 0,
            "sortType": "0",
            "brandIdList": []
        }
        data = json.dumps(data, separators=(',', ':'))
        response = common_request(url, headers=self.headers, cookies=self.login_cookie, data=data, method='POST', proxies_type=True)
        try:
            return math.ceil(int(response.json()['data']['total']) / 20)
        except Exception as e:
            error_msg = f'全国企业采购交易,获取所有页数, 列表解析错误: {e}'
            self.log_info(error_msg)
            self.updata_cookie()
            return 0

    def start_requests(self):
        # 如果是1，从头开始爬
        self.get_cookies()
        is_start = str(self.start_page)
        industry_type = "大宗商品"
        for material_first in self.get_material()[::-1]:
            material_first_type = material_first['gcName']
            # 目前只采建材的
            if material_first_type != '建材':
                continue
            for material_second in material_first['children'][::-1]:
                material_second_type = material_second['gcName']
                for material_third in material_second['children'][::-1]:
                    material_third_type = material_third['gcName']
                    if material_third_type == '卷板':
                        is_start = "1"
                    if is_start == "0":
                        continue
                    material = {
                        'industry_type': industry_type,
                        'material_first_type': material_first_type,
                        'material_second_type': material_second_type,
                        'material_third_type': material_third_type,
                        'material_third_id': material_third['gcId'],
                    }
                    all_page_num = self.get_page_num(material)
                    if all_page_num == 0:
                        all_page_num = self.get_page_num(material)

                    yield from self.get_list(1, material, all_page_num)

    def get_list(self, page, material, total_pages):
        logger.warning(
            f"spider_name: {self.name} Crawling material:{material} page:{page}"
        )

        url = "https://www.cneptp.com/prod-api/zzyc_public/api/goods/price/search"
        payload = {
            "pageNum": int(page),
            "pageSize": 20,
            "keyword": "",
            "propList": [],
            "type": 1,
            "categoryList": [
                {"categoryId": material["material_third_id"]}
            ],
            "sortKey": 0,
            "sortType": "0",
            "brandIdList": [],
        }

        yield scrapy.Request(
            url=url,
            method="POST",
            headers=self.headers,
            cookies=self.login_cookie,
            body=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            callback=self.parse_list,
            cb_kwargs={"material": material, 'page': page, 'total_pages': total_pages},
            errback=self.errback,
        )

    def parse_list(self, response, material, page, total_pages):
        try:
            json_data = response.json()
            for data in json_data['data']['goodsPriceVOList']:
                material_name = data['goodsName']
                material_spec = data['goodsProp']
                unit = data['unit']
                url_list = {
                    'material_name': material_name,
                    'material_spec': material_spec,
                    'unit': unit,
                    'material': material,
                    'unitId': data['unitId'],
                    'productParam': "[]" if data['productParam']is None else data['productParam'],
                }
                yield from self.get_content(url_list)
        except Exception as e:
            error_msg = f'全国企业采购交易, url: {response.url}, 列表解析错误: {e}'
            self.log_info(error_msg)

            # 本页处理完,再发下一页
        if page < total_pages:
            yield from self.get_list(page + 1, material, total_pages)

    def get_area(self, data_data):
        time.sleep(random.uniform(3, 6))
        url = "https://www.cneptp.com/prod-api/zzyc_public/api/enquiry/get-dynamic-region-by-param"
        data = {
            "productId": data_data['material']['material_third_id'],
            "unitId": data_data['unitId'],
            "queryType": "5",
            "params": json.loads(data_data['productParam'].replace('prop_id', 'propId'))
        }
        data = json.dumps(data, separators=(',', ':'))
        response = common_request(url, headers=self.headers, cookies=self.login_cookie, data=data, method='POST', proxies_type=True)
        try:
            return response.json()['data']
        except Exception as e:
            error_msg = f'全国企业采购交易, 获取地区失败, 列表解析错误: {e}'
            self.log_info(error_msg)
            return []


    def get_content(self, list_data):
        logger.warning(f'{self.name} crawling detail:')
        area_list = self.get_area(list_data)
        url = "https://www.cneptp.com/prod-api/zzyc_public/api/enquiry/search/productEnquiryPriceTrendWeek"
        data = {
            "productId": list_data['material']['material_third_id'],
            "unitId": list_data['unitId'],
            "params": json.loads(list_data['productParam'].replace('prop_id', 'propId')),
            "areaCode": 0,
            "areaType": 0
        }
        # 全国
        if True:
            time.sleep(random.uniform(3, 6))
            data_dumps = json.dumps(data, separators=(',', ':'))
            response = common_request(url, headers=self.headers, cookies=self.login_cookie, data=data_dumps, method='POST', proxies_type=True)
            if response:
                data = response.json()
                if data.get('data'):
                    yield from self.parse_content(response, list_data, {"province": "全国", "city": None})
                else:
                    time.sleep(random.uniform(3, 6))
                    response = common_request("https://www.cneptp.com/prod-api/zzyc_public/api/enquiry/search/productEnquiryPriceTrend",headers=self.headers, cookies=self.login_cookie, data=data_dumps,method='POST', proxies_type=True)
                    if response:
                        yield from self.parse_content(response, list_data, {"province": "全国", "city": None})

        #  省市
        for province_area in [] if area_list is None else area_list:
            if province_area['hasData']:
                time.sleep(random.uniform(3, 6))
                data['areaCode'] = int(province_area['code'])
                data['areaType'] = 1
                data_dumps = json.dumps(data, separators=(',', ':'))
                response = common_request(url, headers=self.headers, cookies=self.login_cookie, data=data_dumps, method='POST', proxies_type=True)
                if response:
                    data = response.json()
                    if data.get('data'):
                        yield from self.parse_content(response, list_data, {"province": province_area['name'], "city": None})
                    else:
                        time.sleep(random.uniform(3, 6))
                        response = common_request("https://www.cneptp.com/prod-api/zzyc_public/api/enquiry/search/productEnquiryPriceTrend", headers=self.headers, cookies=self.login_cookie, data=data_dumps,
                                                  method='POST', proxies_type=True)
                        if response:
                            data = response.json()
                            if data.get('data'):
                                yield from self.parse_content(response, list_data,{"province": province_area['name'], "city": None})

                # 市
                for city_area in province_area.get('infos') or []:
                    if city_area['hasData']:
                        time.sleep(random.uniform(3, 6))
                        data['areaCode'] = int(city_area['code'])
                        data['areaType'] = 2
                        data_dumps = json.dumps(data, separators=(',', ':'))
                        response = common_request(url, headers=self.headers, cookies=self.login_cookie, data=data_dumps,
                                                method='POST', proxies_type=True)
                        if response:
                            data = response.json()
                            if data.get('data'):
                                yield from self.parse_content(response, list_data,{"province": province_area['name'], "city": city_area['name']})
                            else:
                                time.sleep(random.uniform(3, 6))
                                response = common_request("https://www.cneptp.com/prod-api/zzyc_public/api/enquiry/search/productEnquiryPriceTrend",headers=self.headers, cookies=self.login_cookie, data=data_dumps,method='POST', proxies_type=True)
                                if response:
                                    data = response.json()
                                    if data.get('data'):
                                        yield from self.parse_content(response, list_data,{"province": province_area['name'],"city": city_area['name']})

    def parse_content(self, response, list_data, area):
        try:
            data = response.json()
            if data.get('data'):
                for data_list in data['data']:
                    market_price = data_list['value']
                    quote_time = data_list['yearWeek']

                    # item_main = MaterialInfoItem()
                    # item_main.spider_name = self.spider_name
                    item_main = {}
                    item_main['industry_type'] = list_data['material']['material_first_type']
                    item_main['material_first_type'] = list_data['material']['material_first_type']
                    item_main['material_second_type'] = list_data['material']['material_second_type']
                    item_main['material_third_type'] = list_data['material']['material_third_type']
                    item_main['material_name'] = list_data['material_name']
                    item_main['img_url'] = None
                    item_main['material_spec'] = None if list_data['material_spec'] is None else json.dumps(list_data['material_spec'])
                    item_main['other_params'] = None
                    item_main['brand'] = None
                    item_main['unit'] = list_data['unit']
                    item_main['engineering_price'] = None
                    item_main['tax_rate'] = None
                    item_main['province'] = area['province']
                    item_main['city'] = area['city']
                    item_main['district'] = None
                    item_main['supplier'] = None
                    item_main['supply_addr'] = None
                    item_main['supply_region'] = None
                    item_main['supply_phone'] = None
                    item_main['supply_person'] = None
                    item_main['quote_time'] = quote_time
                    item_main['market_price'] = market_price
                    item_main['source'] = 'https://www.cneptp.com/'
                    item_main['md5_value'] = hash_md5(f"{list_data['material_name']}{list_data['unitId']}{list_data['material']['material_third_id']}{area['province']}{area['city']}{quote_time}")
                    # item_main.usage = None
                    # insert_data(table='material_info', data=item_main)
                    yield item_main

        except Exception as e:
            error_msg = f'[error] {self.name}, 全国企业采购交易-详情解析失败，错误：{e}'
            logger.exception(error_msg)


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
