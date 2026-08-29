"""
律师事务所爬虫（law_law_firm）
数据来源：12348中国法网（12348.moj.gov.cn）

策略：
  全量拉取，按省份→事务所列表→详情+律师列表三级请求
  律师事务所主记录写入 law_firm_info
  律师信息写入 law_firm_lawyer_info（_table 路由）
  去重字段：md5_value（uscc + establish_date）

本地调试：
  scrapy crawl law_law_firm
"""
from utils.tools import *
import scrapy
from spiders.base_spider import BaseSpider
from utils.decrypt import *


class LawFirmSpider(BaseSpider):
    """律师事务所及律师信息爬虫"""

    name = 'law_law_firm'
    # data_table = 'law_firm_info'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://12348.moj.gov.cn',
        'Referer': 'https://12348.moj.gov.cn/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0',
    }

    cookies = {'crawlerCookie': 'c2d01b2b-b4ad-4628-83a0-ee9a1a59226a'}
    v_key = get_uuid()
    base_url = 'https://12348.moj.gov.cn/lawerdeptlist/getlawerdeptlist'
    detail_url = 'https://12348.moj.gov.cn/lawdeptinfo/getlawdeptinfo'
    lawyer_url = 'https://12348.moj.gov.cn/lawdeptinfo/getlawerlist'
    city_url = 'https://12348.moj.gov.cn/lawerdeptlist/getcitylist'
    district_url = 'https://12348.moj.gov.cn/selectdistrict/getselectdistrict'

    city_data = []

    def generate_data(self, page, area_code):
        # v_key = get_uuid() if page == 1 else self.v_key
        # cookies = {'crawlerCookie': get_uuid()} if page == 1 else self.cookies
        guid = get_uuid()
        number = generate_number(self.v_key, guid, page, page_size=5000)

        json_data = {
            'pageSize': 5000,
            'pageNum': str(page),
            'xzqh': area_code,
            'yw': '',
            'pzslsj': 0,
            'nums': 0,
            'v_key': self.v_key,
            'guid': guid,
            'number': number,
            'crawlerCookie': self.cookies.get('crawlerCookie'),
        }
        return json_data

    def start_requests(self):
        yield scrapy.Request(
            url=self.district_url,
            method='POST',
            headers=self.headers,
            callback=self.get_district
        )

    def get_district(self, response):
        if response:
            result = response.json()
            for data in result:
                code = data['code']
                province = data['name']

                json_data = {'district': code}
                yield scrapy.Request(
                    url=self.city_url,
                    method='POST',
                    headers=self.headers,
                    body=json.dumps(json_data, ensure_ascii=False),
                    callback=self.get_city,
                )
                #
                json_data = self.generate_data(1, code)
                yield scrapy.Request(
                    url=self.base_url,
                    method='POST',
                    headers=self.headers,
                    body=json.dumps(json_data, ensure_ascii=False),
                    cookies=self.cookies,
                    callback=self.parse_list,
                    cb_kwargs={'province': province}
                )



    def get_city(self, response):
        if response:
            result = response.json()
            for data in result:
                code = data['code']
                city = data['name']
                temp = {'code': code, 'city': city}
                self.city_data.append(temp)

    def return_city(self, code):
        result = [i['city'] for i in self.city_data if i.get('code') in code]
        return result[0] if result else None

    def parse_list(self, response, province):
        result = response.json()['list']
        for data in result:
            link = data['lsswsbs']
            people_num = data['nums']
            xzqh = data['xzqh']
            city = self.return_city(xzqh)
            city = province if '市' in province else city
            temp = {'link': link, 'people_num': people_num, 'province': province, 'city': city}
            #
            json_data = {'lsswsbs': temp['link']}
            yield scrapy.Request(
                url=self.detail_url,
                method='POST',
                headers=self.headers,
                body=json.dumps(json_data, ensure_ascii=False),
                callback=self.parse_detail,
                cb_kwargs={'data': temp}
            )
            #
            json_data1 = {'pkid': temp['link'], 'pageNum': 1, 'pageSize': 1000}
            yield scrapy.Request(
                url=self.lawyer_url,
                method='POST',
                headers=self.headers,
                body=json.dumps(json_data1, ensure_ascii=False),
                callback=self.parse_lawyer_list,
            )

    def parse_detail(self, response, data):
        result = response.json()
        try:
            law_firm_name = result['lsswsmc']
            uscc = result['tyshxydm']
        except:
            pass
        else:
            establish_date = result.get('pzslsj')
            tel_number = result.get('zsdh')
            district = result.get('district')
            address = result['zsd']
            abstracts = result['jj']

            items = {}
            # item.spider_name = self.spider_name
            items['law_firm_name'] = law_firm_name
            items['uscc'] = uscc
            items['establish_date'] = establish_date
            items['people_number'] = data['people_num']
            items['tel_number'] = tel_number
            items['province'] = data['province']
            items['city'] = data['city']
            items['district'] = district
            items['address'] = address
            items['abstracts'] = abstracts
            items['md5_value'] = hash_md5(uscc + establish_date)
            # insert_data(table='law_firm_info', data=item)
            items['_table'] = 'law_firm_info'
            yield items


    def parse_lawyer_list(self, response):
        result = response.json()
        res = result['list']
        for data in res:
            law_firm_name = data['lsswsmc']
            lawyer_name = data['xm']
            practise_license_num = data['zyzh']

            items = {}
            # item.spider_name = self.spider_name
            items['law_firm_name'] = law_firm_name
            items['practise_license_num'] = practise_license_num
            items['lawyer_name'] = lawyer_name
            items['md5_value'] = hash_md5(practise_license_num+law_firm_name)
            # insert_data('law_firm_lawyer_info', item)
            items['_table'] = 'law_firm_lawyer_info'
            yield items