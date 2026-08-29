"""土地成交公告爬虫，来源：landchina.mnr.gov.cn"""
import hashlib, scrapy;
import re
from lxml import etree
from spiders.base_spider import BaseSpider
from utils.tools import *

class CjgsLandSpider(BaseSpider):
    name='economy_cjgs_land'
    data_table='entity_land_massif_publicity'
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'
    land_type_key = 'cjgs'
    # 编译正则表达式，提高性能
    page_count_pattern = re.compile(r'var countPage = (.*?)//共多少页', re.S)
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

    def start_requests(self):
        land_type_dict = ['xycr', 'hbgd', 'zbcr', 'gpcr', 'pmcr']
        for land_type in land_type_dict:
            self.log_info(f'当前抓取土地类型: {land_type}')
            land_url = f'https://landchina.mnr.gov.cn/land/{self.land_type_key}/{land_type}/'
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
                # 使用预编译的正则表达式
                match = self.page_count_pattern.search(response.text)
                if match:
                    total_page = match.group(1)
                else:
                    self.log_error(f'未找到总页数，land_type:{land_type}')
                    total_page = None
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

    @staticmethod
    def str_replace(data):
        """统一的字符串清理方法"""
        if isinstance(data, list):
            data = data[0] if data else ""
        if not data:
            return None
        # 统一清理所有需要替换的字符
        return data.strip().replace('\xa0', '').replace('\n', '').replace(' ', '').replace('/', '').replace('\\', '')

    def url_parse(self, response, result, land_type):
        """成交公告解析"""
        details_element = etree.HTML(response.text)
        # 安全获取行政区信息
        region_texts = details_element.xpath('//div[@class="gu-art-data fl"]/text()')
        region = region_texts[1].split('：')[1] if len(region_texts) > 1 and '：' in region_texts[1] else ''
        units = self.str_replace(details_element.xpath('//div[@style="text-align: right;"]/text()'))  # 行政单位

        table_list = details_element.xpath('//div[@class="tabs-class"]/div/table')
        if table_list:
            for table in table_list:
                details_tr_list = table.xpath('./tbody/tr')
                # 使用优化的XPath提取方法
                land_parcel_number = self.str_replace(details_tr_list[0].xpath('string(./td[2])'))  # 宗地编号
                massif_position = self.str_replace(details_tr_list[0].xpath('string(./td[6])'))  # 地块位置
                land_area = self.str_replace(details_tr_list[0].xpath('string(./td[4])'))  # 土地面积（平方米）
                transaction_price = self.str_replace(details_tr_list[2].xpath('string(./td[2])'))  # 成交价格（万元）
                transferee = self.str_replace(details_tr_list[2].xpath('string(./td[4])'))  # 受让单位
                transfer_period = self.str_replace(details_tr_list[1].xpath('string(./td[2])'))  # 出让年限
                land_use = self.str_replace(details_tr_list[1].xpath('string(./td[4])'))  # 土地用途
                entry_name = self.str_replace(details_tr_list[1].xpath('string(./td[6])'))  # 项目名称

                # 安全提取公示期和联系信息
                publicity_period_raw = self.str_replace(
                    details_element.xpath('//div[@class="tabs-class"]/div/p[1]/text()'))
                publicity_period = publicity_period_raw.replace('二、公示期：', '') if publicity_period_raw else ''  # 公示期

                # 提取联系信息（安全索引访问）
                contact_info = self._extract_contact_info(
                    details_element.xpath('//div[@class="tabs-class"]/div/p[last()]//text()')
                )

                # 数据验证：确保关键字段不为空
                if not land_parcel_number or not massif_position:
                    self.log_error(f'关键字段缺失，跳过此记录，url:{result["url"]}')
                    return

                # 创建并填充数据项
                item = self._create_land_deal_item(
                    land_parcel_number, massif_position, land_area, transaction_price,
                    transfer_period, land_use, entry_name, transferee, publicity_period,
                    contact_info, result, region, units, land_type
                )
                # insert_data(table='entity_land_massif_publicity', data=item)
                yield item

        elif details_element.xpath('//table/tr/td[p]'):
            table_list = details_element.xpath('//table/tr/td[p]/table')
            for table in table_list:
                tr = table.xpath('./tr')
                if len(tr) < 6:  # 验证表格行数
                    self.log_error(f'表格结构不完整，跳过，url:{result["url"]}')
                    continue

                # 使用优化的XPath提取
                land_parcel_number = self.str_replace(tr[0].xpath('string(./td[2])'))  # 宗地编号
                massif_position = self.str_replace(tr[0].xpath('string(./td[4])'))  # 地块位置
                land_use = self.str_replace(tr[0].xpath('string(./td[6])'))  # 土地用途
                land_area = self.str_replace(tr[1].xpath('string(./td[2])'))  # 土地面积（平方米）
                transfer_period = self.str_replace(tr[1].xpath('string(./td[4])'))  # 出让年限
                transaction_price = self.str_replace(tr[1].xpath('string(./td[6])'))  # 成交价格（万元）
                transferee = self.str_replace(tr[5].xpath('string(./td[2])'))  # 受让单位

                # 安全提取联系信息
                contact_data = details_element.xpath('//table/tr/td[p]/p')
                publicity_period = ''
                if len(contact_data) > 3:
                    publicity_period_raw = ''.join(contact_data[3].xpath('.//text()'))
                    publicity_period = self.str_replace(publicity_period_raw).replace('二、公示期：',
                                                                                      '') if publicity_period_raw else ''

                # 提取联系信息（第二种格式）
                contact_info = {'issuing_authority': '', 'unit_address': '', 'zip_code': '',
                                'contact_phone_number': '', 'contacts': '', 'email': ''}
                if len(contact_data) > 5:
                    all_data_p = contact_data[5].xpath('./text()')
                    contact_info = self._extract_contact_info(all_data_p)

                # 数据验证
                if not land_parcel_number or not massif_position:
                    self.log_error(f'关键字段缺失，跳过此记录，url:{result["url"]}')
                    continue

                # 创建并填充数据项
                item = self._create_land_deal_item(
                    land_parcel_number, massif_position, land_area, transaction_price,
                    transfer_period, land_use, '', transferee, publicity_period,
                    contact_info, result, region, units, land_type
                )
                # insert_data(table='entity_land_massif_publicity', data=item)
                yield item
        else:
            self.log_error(f"文件内未匹配到数据，url：{result['url']}")

    def _extract_contact_info(self, all_data_p: list) -> dict:
        """安全提取联系信息

        Args:
            all_data_p: XPath提取的文本列表

        Returns:
            包含联系信息的字典
        """
        contact_info = {
            'issuing_authority': '',
            'unit_address': '',
            'zip_code': '',
            'contact_phone_number': '',
            'contacts': '',
            'email': ''
        }

        if not all_data_p or len(all_data_p) < 7:
            return contact_info

        try:
            contact_info['issuing_authority'] = self.str_replace(all_data_p[1]).replace('联系单位：', '') if len(
                all_data_p) > 1 else ''
            contact_info['unit_address'] = self.str_replace(all_data_p[2]).replace('单位地址：', '') if len(
                all_data_p) > 2 else ''
            contact_info['zip_code'] = self.str_replace(all_data_p[3]).replace('邮政编码：', '') if len(
                all_data_p) > 3 else ''
            contact_info['contacts'] = self.str_replace(all_data_p[4]).replace('联系人：', '') if len(
                all_data_p) > 4 else ''
            contact_info['contact_phone_number'] = self.str_replace(all_data_p[5]).replace('联系电话：', '') if len(
                all_data_p) > 5 else ''
            contact_info['email'] = self.str_replace(all_data_p[6]).replace('电子邮件：', '') if len(
                all_data_p) > 6 else ''
        except Exception as e:
            self.log_error(f'提取联系信息失败: {e}')

        return contact_info

    def _create_land_deal_item(self, land_parcel_number: str, massif_position: str,
                               land_area: str, transaction_price: str, transfer_period: str,
                               land_use: str, entry_name: str, transferee: str,
                               publicity_period: str, contact_info: dict,
                               result: dict, region: str, units: str, land_type: str):
        """创建土地成交数据项

        Args:
            各字段参数

        Returns:
            填充好的LandDealItem对象
        """
        md5_value = hash_md5(land_parcel_number + massif_position)
        items = {}
        items['md5_value'] = md5_value
        items['land_file_title'] = result['land_title']
        items['land_parcel_number'] = land_parcel_number
        items['massif_position'] = massif_position
        items['land_area'] = land_area
        items['transaction_price'] = transaction_price
        items['transfer_period'] = transfer_period
        items['land_use'] = land_use
        items['entry_name'] = entry_name
        items['transferee'] = transferee
        items['publicity_period'] = publicity_period
        items['issuing_authority'] = contact_info.get('issuing_authority', '')
        items['contact_unit'] = contact_info.get('issuing_authority', '')
        items['unit_address'] = contact_info.get('unit_address', '')
        items['zip_code'] = contact_info.get('zip_code', '')
        items['contact_phone_number'] = contact_info.get('contact_phone_number', '')
        items['contacts'] = contact_info.get('contacts', '')
        items['email'] = contact_info.get('email', '')
        items['details'] = result['url']
        items['release_date'] = result['release_date']
        items['region'] = region
        items['units'] = units
        items['source'] = land_type
        return items

    def errback(self,failure):self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
