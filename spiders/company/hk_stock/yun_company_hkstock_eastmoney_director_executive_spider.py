from scrapy import FormRequest
from spiders.base_spider import BaseSpider
from utils.mysql_tools import select_data, update_set
from utils.tools import *
from utils.time_kit import *
import time


class YunDirectorExecutiveSpider(BaseSpider):
    name = 'yun_company_hkstock_eastmoney_director_executive'
    default_origin_url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
    headers = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Origin": "https://emweb.securities.eastmoney.com",
        "Referer": "https://emweb.securities.eastmoney.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
    }

    data_table = 'listing_hk_director_executive'
    custom_settings = {
        'CONCURRENT_REQUESTS': 8, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    def start_requests(self):
        code_list = select_data(
            table='stock_hk_hkex', data=['stock_code', 'status'],
            suffix='GROUP BY stock_code ORDER BY stock_code'
        )
        for code in code_list:
            stock_code = code['stock_code']
            status = code['status']
            if status == 1:
                for tags, i in {'董事会': 1, '管理层': 2}.items():
                    # 1：董事会成员，2：管理层成员
                    params = {
                        "reportName": "RPT_HKPCF10_BASIC_EXECUTIVEINFO",
                        "columns": "ALL",
                        "quoteColumns": "",
                        "filter": f'(SECUCODE="{stock_code}.HK")(NUM={i})(PERSON_NAME<>"NULL")',
                        "pageNumber": "1",
                        "pageSize": "200",
                        "sortTypes": "1",
                        "sortColumns": "RN",
                        "source": "F10",
                        "client": "PC",
                    }
                    yield FormRequest(
                        url=self.default_origin_url,
                        method='get',
                        headers=self.headers,
                        formdata=params,
                        meta={'tags': tags, 'stock_code': stock_code},
                        callback=self.parse,
                        dont_filter=True
                    )
            else:
                table_datas = select_data(
                    table='listing_hk_director_executive', data=['md5_value'],
                    condition=f'stock_code = "{stock_code}.HK"'
                )
                table_md5 = [data['md5_value'] for data in table_datas]
                for md5_value in table_md5:
                    item = {
                        'md5_value': md5_value,
                        'status': 0,
                    }
                    update_set(table=self.data_table, data=item)


    def parse(self, response, **kwargs):
        meta = response.meta
        tags = meta['tags']
        stock_code = meta['stock_code']

        result = response.json()
        result = result['result']
        if result:
            md5_value_list = []
            datas = result['data']
            stock_code_data = ''
            for data in datas:
                stock_code = data['SECUCODE']
                person_name = data['PERSON_NAME']
                position = data['POSITION_NAME']
                start_date = data['INCUMBENT_START_DATE']
                end_date = data['INCUMBENT_END_DATE']
                birth_time = data['BRITH_YEAR']
                gender = data['SEX']
                education = data['HIGH_DEGREE']
                update_date = data['UPDATE_DATE']
                summary = data['RESUME']
                md5_value = hash_md5(f"{stock_code}{person_name}{gender}{str(birth_time)}{position}")
                md5_value_list.append(md5_value)
                stock_code_data = stock_code


                item = {}
                item['md5_value']=md5_value
                item['stock_code']=stock_code
                item['tags']=tags
                item['person_name']=person_name
                item['gender']=gender
                item['birth_time']=birth_time
                item['position']=position
                item['start_date']=start_date
                item['end_date']=end_date
                item['education']=education
                item['summary']=summary
                item['update_date']=update_date
                item['status']=1

                yield item

            # 判断是否为历史数据
            table_datas = select_data(
                table='listing_hk_director_executive', data=['md5_value'],
                condition=f'stock_code = "{stock_code_data}" AND tags = "{tags}"'
            )
            table_md5 = [data['md5_value'] for data in table_datas]
            for md5_value in table_md5:
                if md5_value not in md5_value_list:
                    item = {
                        'md5_value': md5_value,
                        'status': 0,
                    }
                    yield item
        else:
            # 如果不存在将该股票所有的全变成历史
            # 判断是否为历史数据
            table_datas = select_data(
                table='listing_hk_director_executive', data=['md5_value'],
                condition=f'stock_code = "{stock_code}" AND tags = "{tags}"'
            )
            table_md5 = [data['md5_value'] for data in table_datas]
            for md5_value in table_md5:
                item = {
                    'md5_value': md5_value,
                    'status': 0,
                }
                yield item

