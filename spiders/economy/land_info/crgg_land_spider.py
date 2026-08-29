"""土地出让公告爬虫，来源：landchina.mnr.gov.cn"""
import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *
from datetime import datetime


class CrggLandSpider(BaseSpider):
    name='economy_crgg_land'
    data_table='entity_land_transfer_announcement'
    custom_settings = {
        'CONCURRENT_REQUESTS': 4, 'DOWNLOAD_DELAY': 0.5,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    land_type_key = 'crgg'
    headers = {
        'Host': 'landchina.mnr.gov.cn',
        'Connection': 'keep-alive',
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
        'sec-ch-ua-mobile': '?0',
        # 'sec-ch-ua-platform': '"Windows"',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    @staticmethod
    def str_replace(data):
        if isinstance(data, list):
            data = data[0] if data else ""
        return data.strip().replace('\xa0', '').replace('\n', '').replace(' ', '') if data else ""

    def start_requests(self):
        land_type_dict = ['gyyd', 'syyd', 'zzyd', 'qtyd', 'zbgg', 'pmgg', 'gpgg', 'gkgg']
        for land_type in land_type_dict:
            self.log_info(f'当前抓取土地类型: {land_type}')
            land_url = 'https://landchina.mnr.gov.cn/land/{}/{}/'.format(self.land_type_key, land_type)
            yield scrapy.Request(
                url=land_url,
                headers=self.headers,
                callback=self.get_count_page,
                cb_kwargs={'land_type': land_type},
            )

    def get_count_page(self, response, land_type):
        """获取页面数据总页数

        Args:
            land_type: 土地类型

        Returns:
            总页数字符串，失败返回None
        """
        if response:
            try:
                total_page = re.search('.*?var countPage = (.*?)//共多少页', response.text, re.S).group(1)
            except:
                total_page = None
            if int(self.end_page) < 0:
                count_page = int(total_page) if total_page else 2
            else:
                count_page = self.end_page
            for page in range(self.start_page - 1, count_page):
                """请求获取列表页"""
                if page == 0:
                    land_url = 'https://landchina.mnr.gov.cn/land/{}/{}/index.htm'.format(self.land_type_key,
                                                                                          land_type)
                else:
                    land_url = 'https://landchina.mnr.gov.cn/land/{}/{}/index_{}.htm'.format(self.land_type_key,
                                                                                             land_type, page)
                yield scrapy.Request(
                    url=land_url,
                    headers=self.headers,
                    callback=self.get_list,
                    cb_kwargs={'land_type': land_type},
                )

    def get_list(self, response, land_type):
        """得到每个具体页面的url"""
        land_list_element = etree.HTML(response.text)
        land_element_uls = land_list_element.xpath('//div[@class="gu-ky-list"]/ul')
        for land_element_ul in land_element_uls:
            for land_element_li in land_element_ul.xpath('./li'):
                release_date = self.str_replace(land_element_li.xpath('./span/text()'))
                land_title = self.str_replace(land_element_li.xpath('./a/text()'))
                land_href = land_element_li.xpath('./a/@href')[0].replace('./', '')
                url = f'https://landchina.mnr.gov.cn/land/{self.land_type_key}/{land_type}/{land_href}'
                result = {'release_date': release_date, 'land_title': land_title, 'url': url}
                yield scrapy.Request(
                    url=url,
                    headers=self.headers,
                    callback=self.url_parse,
                    cb_kwargs={'result': result, 'land_type': land_type},
                )

    def url_parse(self, response, result, land_type):
        """url公告内部数据解析 """
        details_element = etree.HTML(response.text)
        elements = self.str_replace(details_element.xpath('//div[@class="min-title"]/div[2]/text()'))  # 公告编号

        region = details_element.xpath('//div[@class="gu-art-data fl"]/text()')[1].split('：')[1]  # 行政区

        transfer_manner = self.str_replace(
            details_element.xpath('//div[@style="text-align: left;"]/div[1]/u[1]/text()'))  # 出让方式

        units = self.str_replace(details_element.xpath('//div[@style="text-align: right;"]/text()'))  # 行政单位

        table_list = details_element.xpath('//div[@class="tabs-class"]/div/table')
        for table in table_list:
            details_tr_list = table.xpath('./tbody/tr')
            land_location = self.str_replace(details_tr_list[0].xpath('./td[6]//text()'))  # land_location	土地坐落
            land_parcel_number = self.str_replace(
                details_tr_list[0].xpath('./td[2]//text()'))  # land_parcel_number	宗地编号
            area = self.str_replace(details_tr_list[0].xpath('./td[4]//text()'))  # area	面积（平方米）
            transfer_period = self.str_replace(details_tr_list[1].xpath('./td[2]//text()'))  # transfer_period	出让年限
            floor_area_ratio = self.str_replace(
                ''.join(details_tr_list[1].xpath('./td[4]//text()')))  # floor_area_ratio	容积率
            building_density = self.str_replace(
                ''.join(details_tr_list[1].xpath('./td[6]//text()')))  # building_density	建筑密度（%）
            greening_rate = self.str_replace(
                ''.join(details_tr_list[2].xpath('./td[2]//text()')))  # greening_rate	绿化率（%）
            building_height_limit = self.str_replace(
                ''.join(details_tr_list[2].xpath('./td[4]//text()')))  # building_height_limit	建筑限高
            land_use = self.str_replace(''.join(details_tr_list[4].xpath('./td[1]//text()')))  # land_use	土地用途

            guarantee_price, starting_price, price_increase, listing_time, listing_start_time, listing_end_time, release_date = '', '', '', '', '', '', ''
            for i in range(8, 11):
                guarantee_price_name = self.str_replace(
                    ''.join(details_tr_list[i].xpath('./td[3]//text()')))
                if '保证金' in guarantee_price_name:
                    guarantee_price = self.str_replace(
                        ''.join(details_tr_list[i].xpath('./td[4]//text()')))  # guarantee_price 保证金（万元）
                    break
            for i in range(9, 12):
                starting_price_name = self.str_replace(
                    ''.join(details_tr_list[i].xpath('./td[1]//text()')))
                if '起始价' in starting_price_name:
                    starting_price = self.str_replace(
                        ''.join(details_tr_list[i].xpath('./td[2]//text()')))  # starting_price	起始价（万元）
                    price_increase = self.str_replace(
                        ''.join(details_tr_list[i].xpath('./td[4]//text()')))  # price_increase	加价幅度（万元）
                    break
            for i in range(-3, 0):
                listing_time_name = self.str_replace(
                    ''.join(details_tr_list[i].xpath('./td[1]//text()')))
                if '时间' in listing_time_name:
                    listing_start_time = self.str_replace(
                        ''.join(details_tr_list[i].xpath('./td[2]//text()')).replace('年', '-').replace('月',
                                                                                                        '-').replace(
                            '日', ''))
                    listing_start_time = datetime.strptime(listing_start_time, "%Y-%m-%d").strftime("%Y-%m-%d")
                    listing_end_time = self.str_replace(
                        ''.join(details_tr_list[i].xpath('./td[4]//text()')).replace('年', '-').replace('月',
                                                                                                        '-').replace(
                            '日', ''))
                    listing_end_time = datetime.strptime(listing_end_time, "%Y-%m-%d").strftime("%Y-%m-%d")
                    # listing_time = self.str_replace(
                    #     ''.join(details_tr_list[i].xpath('./td[2]//text()'))) + '-' + self.str_replace(
                    #     ''.join(details_tr_list[i].xpath('./td[4]//text()')))
                    break

            md5_value = hash_md5(land_parcel_number + land_location)
            items = {}
            items['md5_value'] = md5_value
            items['details'] = result['url']  # details	详情
            items['land_file_title'] = result['land_title']
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
            items['listing_start_time'] = listing_start_time
            items['listing_end_time'] = listing_end_time
            items['release_date'] = result['release_date']
            items['source'] = land_type
            items['elements'] = elements
            # insert_data(table='entity_land_transfer_announcement', data=item)
            yield items

    def errback(self,failure):self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
