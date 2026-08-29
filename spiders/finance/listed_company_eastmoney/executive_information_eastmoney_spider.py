import hashlib, scrapy
import math
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.finance.listed_company_eastmoney.fs_key_value import fs_value
from utils.mysql_tools import select_data
from utils.tools import *
from utils.time_kit import *

# https://quote.eastmoney.com/center/gridlist.html#hs_a_board
# 公司高管
class ExecutiveInformationEastmoneySpider(BaseSpider):
    name = 'executive_information_eastmoney'
    data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 8, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        },
        #'COOKIES_ENABLED': True  # 使用cookie字段必须得要
    }
    proxy_type = 'long_proxy'

    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Referer": "https://quote.eastmoney.com/center/gridlist.html",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": "\"Not;A=Brand\";v=\"8\", \"Chromium\";v=\"150\", \"Google Chrome\";v=\"150\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    def start_requests(self):
        code_list = select_data(
            table='stock_hsj', data=['stock_code', 'status', 'area'],
            suffix='GROUP BY stock_code ORDER BY stock_code'
        )
        for code in code_list:
            stock_code = code['stock_code']
            status = code['status']
            f13 = code['area']
            if status == 1 or status == '1':
                logger.warning(f"stock_code:{stock_code}")
                old_url = f"https://quote.eastmoney.com/unify/r/{f13}.{stock_code}"
                yield scrapy.Request(
                    url=old_url,
                    method="GET",
                    headers=self.headers,
                    callback=self.parse_details_url,
                    cb_kwargs={'f13': f13}
                )

    def parse_details_url(self, response, f13):
        new_url = response.url
        url_key = new_url.replace('//quote.eastmoney.com/', '').replace('/', '').replace('.html', '').replace(
            'https:', '').upper()
        prefix, code = re.match(r"([A-Za-z]+)(\d+)", url_key).groups()
        if f13 == 1 or f13 == "1":
            prefix = "SH"
        details_url = f"https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code={prefix}{code}&color=b#/gsgg"
        yield from self.get_details({'detail_url': details_url, 'code': code, 'prefix': prefix})

    def get_details(self, data):
        logger.warning(f"spider_name:{self.name} data:{data}")
        code = data['code']
        prefix = data['prefix']
        url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        params = {
            "reportName": "RPT_F10_ORGINFO_MANAINTRO",
            "columns": "ALL",
            "quoteColumns": "",
            "filter": f'(SECUCODE="{code}.{prefix}")',
            "pageNumber": "1",
            "pageSize": "",
            "sortTypes": "",
            "sortColumns": "",
            "source": "HSF10",
            "client": "PC",
            "v": ""
        }
        yield scrapy.Request(
            url=f"{url}?{urlencode(params)}",
            headers=self.headers,
            callback=self.parse_details,
            cb_kwargs={'base_data': data}
        )

    def extract_birth_year(self, text):
        """
        提取距离“生”或“出生”最近的出生年份。
        匹配格式：
        1985年生
        1979年出生
        1984年8月生
        1984年8月出生
        未匹配到时返回 None。
        """
        pattern = r'((?:19|20)\d{2})(?=年(?:\d{1,2}月)?(?:出生|生))'

        match = re.search(pattern, text or '')
        return match.group(1) if match else None

    def parse_details(self, response, base_data):
        json_data = response.json()
        if json_data['result']:
            md5_value_list = []
            share_code_data = base_data['code']
            for data in json_data['result'].get('data', []):
                share_code = base_data['code']  # 股票代码
                executive_name = data['PERSON_NAME']    # 高管姓名
                sex = data['SEX']   # 性别

                birth_year = self.extract_birth_year(data['RESUME'])    # 出生年份
                if birth_year and birth_year == data['BIRTH_YEAR']:
                    birth_year = birth_year
                elif birth_year:
                    birth_year = birth_year
                else:
                    birth_year = data['BIRTH_YEAR']

                ducational_background = data['HIGH_DEGREE']     # 学历
                hold_num = data['HOLD_NUM'] # 持股数(股)
                salary = data['SALARY']     # 薪酬(元)
                position = data['POSITION'] # 职务
                incumbent_time = data['INCUMBENT_TIME'] # 在职时间
                resume = data['RESUME'] # 简历
                source = base_data['detail_url']   #来源网址
                basic_data = json.dumps(data, ensure_ascii=False)

                md5_value = hash_md5(f"{share_code}{executive_name}{sex}{birth_year}")   # Md5值
                md5_value_list.append(md5_value)

                main_item = {}
                main_item['share_code'] = share_code
                main_item['executive_name'] = executive_name
                main_item['sex'] = sex
                main_item['birth_year'] = birth_year
                main_item['ducational_background'] = ducational_background
                main_item['hold_num'] = hold_num
                main_item['salary'] = salary
                main_item['position'] = position
                main_item['incumbent_time'] = incumbent_time
                main_item['resume'] = resume
                main_item['status'] = 1
                main_item['source'] = source
                main_item['md5_value'] = md5_value
                # insert_data('listing_stock_executive', main_item)
                main_item['basic_data'] = basic_data


                main_item['_table'] = 'listing_stock_executive'
                yield main_item

            # 判断是否为历史数据
            table_datas = select_data(
                table='listing_stock_executive',
                data=['md5_value'],
                condition=f'share_code = "{share_code_data}"'
            )
            table_md5 = [data['md5_value'] for data in table_datas]
            for md5_value in table_md5:
                if md5_value not in md5_value_list:
                    # update_data(table_name='listing_stock_executive', data={'status': 0, 'md5_value': md5_value}, condition=f'md5_value="{md5_value}"')
                    main_item = {}
                    main_item['md5_value'] = md5_value
                    main_item['status'] = 0
                    main_item['_table'] = 'listing_stock_executive'
                    yield main_item


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')