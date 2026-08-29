"""土地结果公告爬虫，来源：landchina.mnr.gov.cn → entity_land_contract_signing"""
import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *


class JgggLandSpider(BaseSpider):
    name = 'economy_jggg_land'
    data_table = 'entity_land_contract_signing'
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

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
    land_type_key = 'jggg'

    @staticmethod
    def str_replace(data):
        if isinstance(data, list):
            data = data[0] if data else ""
        return data.strip().replace('\xa0', '').replace('\n', '').replace(' ', '').replace('空值', '') if data else ''

    def start_requests(self):
        land_type_dict = ['hbgd1', 'zbcr1', 'pmcr1', 'gpcr1', 'xycr']
        for land_type in land_type_dict:
            self.log_info(f'当前抓取土地类型:{land_type} ')
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
        land_list_element = etree.HTML(response.text)
        land_element_uls = land_list_element.xpath('.//div[@class="gu-ky-list"]/ul')
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
        table_list = details_element.xpath('//div[@class="gu-art-con"]/table')
        for table in table_list:
            details_tr_list = table.xpath('./tr')
            administrative_region = self.str_replace(
                '.'.join(details_tr_list[1].xpath('./td[2]//text()')))  # administrative_region	行政区
            # electronic_supervision_number = ''  # electronic_supervision_number	电子监督号
            entry_name = self.str_replace('.'.join(details_tr_list[2].xpath('./td[2]//text()'))).replace('"',
                                                                                                         "'")  # entry_name	项目名称
            if not entry_name:
                continue
            project_location = self.str_replace(
                '.'.join(details_tr_list[3].xpath('./td[2]//text()')))  # project_location	项目位置
            area = self.str_replace('.'.join(details_tr_list[4].xpath('./td[2]//text()'))) + '公顷'  # area	面积（平方米）
            # land_source = ''  # land_source	土地来源
            land_use = self.str_replace('.'.join(details_tr_list[5].xpath('./td[2]//text()')))  # land_use	土地用途
            land_supply_method = self.str_replace(
                '.'.join(details_tr_list[5].xpath('./td[4]//text()')))  # land_supply_method	供地方式
            land_use_period = self.str_replace(
                '.'.join(details_tr_list[6].xpath('./td[2]//text()')))  # land_use_period	土地使用年限
            industry_classification = self.str_replace(
                '.'.join(details_tr_list[6].xpath('./td[4]//text()')))  # industry_classification	行业分类
            land_level = self.str_replace('.'.join(details_tr_list[7].xpath('./td[2]//text()')))  # land_level	土地级别
            transaction_price = self.str_replace(
                '.'.join(details_tr_list[7].xpath('./td[4]//text()')))  # transaction_price	成交价格（万元）
            land_use_rights_holder = self.str_replace(
                '.'.join(details_tr_list[9].xpath('./td[2]//text()')))  # land_use_rights_holder	土地使用权人
            approval_unit = self.str_replace(
                '.'.join(details_tr_list[13].xpath('./td[2]//text()')))  # # approval_unit	批准单位
            contract_signing_date = self.str_replace(
                '.'.join(details_tr_list[13].xpath('./td[4]//text()')))  # contract_signing_date	合同签订日期
            agreed_delivery_date = self.str_replace(
                '.'.join(details_tr_list[10].xpath('./td[4]//text()')))  # agreed_delivery_date	约定交地日期
            agreed_commencement_time = self.str_replace(
                '.'.join(details_tr_list[11].xpath('./td[2]//text()')))  # agreed_commencement_time	约定开工时间
            agreed_completion_time = self.str_replace(
                '.'.join(details_tr_list[11].xpath('./td[4]//text()')))  # agreed_completion_time	约定竣工时间
            actual_start_time = self.str_replace(
                '.'.join(details_tr_list[12].xpath('./td[2]//text()')))  # actual_start_time	实际开工时间
            actual_completion_time = self.str_replace(
                '.'.join(details_tr_list[12].xpath('./td[4]//text()')))  # actual_completion_time	实际竣工时间
            agreed_lower_limit = self.str_replace(
                '.'.join(details_tr_list[10].xpath('./td[2]/table/tr/td[2]//text()')))  # agreed_lower_limit	约定容积率下限
            agreed_upper_limit = self.str_replace(
                '.'.join(details_tr_list[10].xpath('./td[2]/table/tr/td[4]//text()')))  # agreed_upper_limit	约定容积率上限
            details = result['url']

            md5_value = hash_md5(entry_name + project_location)
            items = {}
            items['md5_value'] = md5_value
            items['administrative_region'] = administrative_region
            # item.electronic_supervision_number = electronic_supervision_number
            items['entry_name'] = entry_name
            items['project_location'] = project_location
            items['area'] = area
            items['land_source'] = land_type
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
            items['actual_start_time'] = actual_start_time
            items['actual_completion_time'] = actual_completion_time
            items['agreed_lower_limit'] = agreed_lower_limit
            items['agreed_upper_limit'] = agreed_upper_limit
            items['details'] = details
            # insert_data(table='entity_land_contract_signing', data=item)
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
