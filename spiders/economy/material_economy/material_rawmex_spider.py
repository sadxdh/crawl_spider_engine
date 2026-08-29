import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class MaterialRawmexSpider(BaseSpider):
    name = 'economy_material_rawmex'
    data_table = 'material_info'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 5, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        },
        # 'RETRY_ENABLED': True,
        # "RETRY_HTTP_CODES": [566],
        # "RETRY_TIMES": 3,  # 失败重试
        #'COOKIES_ENABLED': True  # 使用cookie字段必须得要
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive',
        'Referer': 'https://www.rawmex.cn/',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    def start_requests(self):
        url = "https://www.rawmex.cn/"
        yield scrapy.Request(
            url=url,
            method='GET',
            headers=self.headers,
            callback=self.get_industry_type
        )

    def get_industry_type(self, response):
        soup = BeautifulSoup(response.text, 'lxml')
        for industry_type_name in soup.select('.toplevel'):
            if industry_type_name.a.text.strip() == '商品板块':
                for type_list in industry_type_name.select('.sub-menu>table>tbody>tr>td>ul>li'):
                    if type_list.a is None:
                        continue
                    type_name = type_list.a.text.strip()
                    type_url = type_list.a['href']
                    if type_name in ['钢铁', '建材']:
                        yield scrapy.Request(
                            url=type_url,
                            method='GET',
                            headers=self.headers,
                            callback=self.get_material_third_type,
                            cb_kwargs={'industry_type': type_name},
                            dont_filter=True
                        )

    def get_material_third_type(self, response, industry_type):
        soup = BeautifulSoup(response.text, 'lxml')
        for material_third_type_li in soup.select('.inner-container>ul>a'):
            base_url = urljoin(response.url, material_third_type_li['href'])
            material_third_type = material_third_type_li.text.strip()
            yield from self.get_page_list(base_url, 1, industry_type, material_third_type)


    def get_page_list(self, base_url, page, industry_type, material_third_type):
        self.log_info(f"正在采集{industry_type}>>{material_third_type}>第{page}页")
        req_url = f"{base_url.rstrip('/')}-{page}"
        yield scrapy.Request(
            url=req_url,
            method='GET',
            headers=self.headers,
            callback=self.parse_list,
            cb_kwargs={'industry_type': industry_type, 'page': page, 'base_url': base_url, 'material_third_type': material_third_type}
        )

    def parse_list(self, response, industry_type, page, base_url, material_third_type):
        soup = BeautifulSoup(response.text, 'lxml')
        for tr_list in soup.select('.element_z>table>tr'):
            if tr_list.a is None:
                continue
            detail_url = urljoin(response.url, tr_list.a['href'])
            yield scrapy.Request(
                url=detail_url,
                method='GET',
                headers=self.headers,
                callback=self.parse_details,
                cb_kwargs={'industry_type_value': industry_type, 'material_third_type_value': material_third_type},
                dont_filter=True,
            )

        if len(soup.select('.element_z>table>tr')) == 21:
            page += 1
            if self.end_page < 1:
                yield from self.get_page_list(base_url, page, industry_type, material_third_type)
            else:
                if page <= self.end_page:
                    yield from self.get_page_list(base_url, page, industry_type, material_third_type)


    def parse_details(self, response, industry_type_value, material_third_type_value):
        soup = BeautifulSoup(response.text, 'lxml')
        data_data = self.get_details_data(soup)
        industry_type = industry_type_value
        material_first_type = industry_type_value
        material_second_type = industry_type_value
        material_third_type = material_third_type_value
        material_name = data_data.get('material_name')
        img_url = data_data.get('img_url')
        other_params = data_data.get('other_params')
        market_price_unit = data_data.get('market_price_unit')
        province_city_district = data_data.get('province_city_district')
        supplier = data_data.get('supplier')
        supply_person = data_data.get('supply_person')
        supply_addr = data_data.get('supply_addr')
        supply_phone = data_data.get('supply_phone')
        quote_time = data_data.get('quote_time')
        if material_name and market_price_unit and quote_time:
            market_price = market_price_unit.split(' ')[0]
            unit = market_price_unit.split(' ')[1]
            if province_city_district:
                province, city, district = self.split_region(province_city_district)
            else:
                province, city, district = None, None, None

            md5_value = hash_md5(f"{response.url}{material_name}{quote_time}")

            main_item = {}
            main_item['industry_type'] = industry_type
            main_item['material_first_type'] = material_first_type
            main_item['material_second_type'] = material_second_type
            main_item['material_third_type'] = material_third_type
            main_item['material_name'] = material_name
            main_item['img_url'] = img_url
            main_item['other_params'] = other_params
            main_item['market_price'] = market_price
            main_item['unit'] = unit
            main_item['province'] = province
            main_item['city'] = city
            main_item['district'] = district
            main_item['supplier'] = supplier
            main_item['supply_addr'] = supply_addr
            main_item['supply_person'] = supply_person
            main_item['supply_phone'] = supply_phone
            main_item['quote_time'] = quote_time
            main_item['md5_value'] = md5_value
            main_item['source'] = "https://www.rawmex.cn/"
            yield main_item


    def split_region(self, value):
        parts = [re.sub(r"\s+", "", x) for x in value.split(">")]
        parts = [x for x in parts if x]
        return (parts + [None, None, None])[:3]

    def get_details_data(self, soup):
        key_name_dict_base = {
            "供应": "material_name",
            "单价": "market_price_unit",
            '规格': "other_params",
            '提货地': "province_city_district",
            '交货地': "province_city_district",
            '发布时间': 'quote_time',
            "一口价": "market_price_unit",
        }
        key_name_dict_supply = {
            "联系人": "supply_person",
            "地址": "supply_addr",
            '手机': "supply_phone",
        }

        data_data = {}
        # 基础信息
        for detail_li in soup.select('[class="box2-2-1-1 dis-flex"]>.d-buy-ul>li'):
            if detail_li.select('[class="tab-gy tab-qg_a"]') == []:
                if detail_li.select('.tyname1') and detail_li.select('.tydetail'):
                    li_name = detail_li.select('.tyname1')[0].text.strip()
                    li_value = detail_li.select('.tydetail')[0].text.strip()
            else:
                li_name = detail_li.select('[class="tab-gy tab-qg_a"]')[0].text.strip()
                li_value = detail_li.select('.tab-qg_a_name')[0].text.strip()
            clean_text = re.sub(r'\s+', '', li_name)
            key_name = key_name_dict_base.get(clean_text)
            if key_name:
                data_data[key_name] = li_value
        if soup.select('.jqzoom'):
            img = soup.select('.jqzoom')[0]['src']
            img_url = urljoin('https://www.rawmex.cn/', img)
            if img_url != 'https://www.rawmex.cn/ui/images/web/member/category/nopic.jpg' and "Array" not in img_url:
                data_data['img_url'] = img_url

        # 供应商信息
        for detail_li in soup.select('[class="justify-direction-column w-20"]>[class="box-bk2 mb-3"]>.otlink1>.d-buy-ul>li'):
            if detail_li.select('.adid1') and detail_li.select('.adress1'):
                li_name = detail_li.select('.adid1')[0].text.strip().replace('：', '')
                li_value = detail_li.select('.adress1')[0].text.strip()
            clean_text = re.sub(r'\s+', '', li_name)
            key_name = key_name_dict_supply.get(clean_text)
            if key_name:
                data_data[key_name] = li_value
        # 供应商名称
        if soup.select('[class="justify-direction-column w-20"]>[class="box-bk2 mb-3"]>[class="jjhy-bk_s px-3"]'):
            supplier = soup.select('[class="justify-direction-column w-20"]>[class="box-bk2 mb-3"]>[class="jjhy-bk_s px-3"]')[0].a.text.strip()
        else:
            supplier = soup.select('[class="justify-direction-column w-20"]>[class="box-bk2 mb-3"]>.otlink1>.d-buy-ul>li')[0].select('.adress1')[0].text.strip()
        data_data['supplier'] = supplier
        return data_data


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')