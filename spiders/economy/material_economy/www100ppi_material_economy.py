from urllib.parse import urlencode
import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class EconomyWww100ppiMaterial_spider(BaseSpider):
    name = 'economy_www_100ppi_material'
    data_table = 'material_info'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 3, 'DOWNLOAD_DELAY': 2,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "sec-ch-ua": "\"Chromium\";v=\"146\", \"Not-A.Brand\";v=\"24\", \"Google Chrome\";v=\"146\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    def start_requests(self):
        url = "https://www.100ppi.com/mprice/"
        yield scrapy.Request(
            url=url,
            method='GET',
            headers=self.headers,
            callback=self.get_material
        )

    def get_material(self, response):
        soup = BeautifulSoup(response.text, 'lxml')
        for data_data in soup.select('.p_list2>ul>li'):
            industry_type = data_data.a.text.strip()
            # 目前只采建材的
            if industry_type != '建材':
                continue
            for data in data_data.select('.tylist1>a'):
                material_third_type = data.text.strip()
                base_url = urljoin(response.url, data['href'])
                material = {'industry_type': industry_type, 'material_third_type': material_third_type, 'base_url': base_url}
                yield from self.get_page_req(1, material)


    def get_page_req(self, page, material):
        base_url_page = re.sub(r'-\d+\.html$', f'-{page}.html', material['base_url'])
        yield scrapy.Request(
            url=base_url_page,
            method='GET',
            headers=self.headers,
            callback=self.parse_list,
            cb_kwargs={'material': material, "page": page}
        )

    def parse_list(self, response, material, page):
        soup = BeautifulSoup(response.text, 'lxml')
        for data in soup.select('.lp-table>tr'):
            if data.a is None:
                continue
            material_url = urljoin("https://www.100ppi.com/mprice/", data.a['href'])
            material_name = data.select('td')[0].text.strip()
            other_params = data.select('td')[1].text.strip()
            match = re.match(r'^(\d+(?:\.\d+)?)\s*(.*)$', data.select('td')[3].text.strip())
            market_price = match.group(1)
            unit = match.group(2)
            province = data.select('td')[5].text.split('/')[0].replace('\t', '').replace('\n', '').replace('\r', '').strip()  if '--' not in data.select('td')[5].text.split('/')[0] else None
            city = data.select('td')[5].text.split('/')[1].replace('\t', '').replace('\n', '').replace('\r', '').strip() if len(data.select('td')[5].text.split('/')) > 1 else None
            quote_time = data.select('td')[7].text.strip()
            brand = data.select('td')[2].text.strip()
            url_list_data = {
                'material_url': material_url,
                'material_name': material_name,
                'other_params': other_params,
                'market_price': market_price,
                'unit': unit,
                'province': province,
                'city': city,
                'quote_time': quote_time,
                'brand': brand,
                'material': material,
            }
            yield scrapy.Request(
                url=url_list_data['material_url'],
                method='GET',
                headers=self.headers,
                callback=self.parse_content,
                cb_kwargs={'list_data': url_list_data}
            )
        if soup.select('.lp-table>tr a') != []:
            page += 1
            yield from self.get_page_req(page, material)


    def parse_content(self, response, list_data):
        soup = BeautifulSoup(response.text, 'lxml')
        if soup:
            supplier = None
            supply_person = None
            supply_phone = None
            for data in soup.select('[class="mb20 st2-table tac"]>tr'):
                try:
                    if data.select('th')[0].text.strip() == '公司名称':
                        supplier = data.select('td')[0].a.text.strip()
                    if data.select('th')[0].text.strip() == '联系人':
                        supply_person = data.select('td')[0].text.strip()
                    if data.select('th')[0].text.strip() == '手机':
                        supply_phone = data.select('td')[0].text.strip()
                except:
                    continue

            item_mains = {}
            item_mains['industry_type'] = list_data['material']['industry_type']
            item_mains['material_first_type'] = list_data['material']['material_third_type']
            item_mains['material_second_type'] = list_data['material']['material_third_type']
            item_mains['material_third_type'] = list_data['material']['material_third_type']
            item_mains['material_name'] = list_data['material_name']
            item_mains['img_url'] = None
            item_mains['material_spec'] = None
            item_mains['other_params'] = list_data['other_params']
            item_mains['brand'] = list_data['brand']
            item_mains['unit'] = list_data['unit']
            item_mains['engineering_price'] = None
            item_mains['tax_rate'] = None
            item_mains['province'] = list_data['province']
            item_mains['city'] = list_data['city']
            item_mains['district'] = None
            item_mains['supplier'] = supplier
            item_mains['supply_addr'] = None
            item_mains['supply_region'] = None
            item_mains['supply_phone'] = supply_phone
            item_mains['supply_person'] = supply_person
            item_mains['quote_time'] = list_data['quote_time']
            item_mains['market_price'] = list_data['market_price']
            item_mains['source'] = 'https://www.100ppi.com/'
            item_mains['md5_value'] = hash_md5(f"{list_data['material_name']}{list_data['material_url']}{list_data['quote_time']}")
            # item_main.usage = None
            # insert_data(table='material_info', data=item_main)
            yield item_mains

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')