import hashlib, scrapy
import math
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.finance.listed_company_eastmoney.fs_key_value import fs_value
from utils.mysql_tools import select_data
from utils.tools import *
from utils.time_kit import *


# https://quote.eastmoney.com/center/gridlist.html#hs_a_board
#  公司大事 重大事项 股权质押
class SharePledgeEastmoneySpider(BaseSpider):
    name = 'share_pledge_eastmoney'
    data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 8, 'DOWNLOAD_DELAY': 0.3,
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
            if status == 1 or status == "1":
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
        details_url = f"https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code={prefix}{code}&color=b#/gsds"
        yield from self.get_details({'detail_url': details_url, 'code': code, 'prefix': prefix})

    def get_details(self, data):
        code = data['code']
        prefix = data['prefix']
        url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        params = {
            "reportName": "RPTA_APP_ACCUMDETAILS",
            "columns": "ALL",
            "quoteColumns": "",
            "filter": f'(SECUCODE="{code}.{prefix}")',
            "pageNumber": "1",
            "pageSize": "200",
            "sortTypes": "-1,-1,-1,-1",
            "sortColumns": "NOTICE_DATE,UNFREEZE_DATE,ACTUAL_UNFREEZE_DATE,PF_START_DATE",
            "source": "HSF10",
            "client": "PC",
            "v": ""
        }
        yield scrapy.Request(
            url=f"{url}?{urlencode(params)}",
            headers=self.headers,
            callback=self.parse_details,
            errback=self.errback,
            cb_kwargs={'base_data': data}
        )

    def parse_details(self, response, base_data):
        json_data = json.loads(response.text)
        if json_data['result']:
            for data in json_data['result'].get('data', []):
                share_code = base_data['code']  # 股票代码
                notice_date = data['NOTICE_DATE']  # 公告日期
                holder_name = data['HOLDER_NAME']  # 股东名称
                pf_org = data['PF_ORG']  # 质押方
                is_pftype = data['IS_PFTYPE']  # 是否质押式回购
                pf_num = data['PF_NUM']  # 质押股数(股)
                pf_tsr = data['PF_TSR']  # 占总股本比例(%)
                pf_hold_ratio = data['PF_HOLD_RATIO']  # 占股东持股比例(%)
                pf_start_date = data['PF_START_DATE']  # 质押起始日
                unfreeze_date = data['UNFREEZE_DATE']  # 质押截止日
                actual_unfreeze_date = data['ACTUAL_UNFREEZE_DATE']  # 解押日期
                unfreeze_state = data['UNFREEZE_STATE']  # 质押状态
                source = base_data['detail_url']    # 来源网址
                basic_data = json.dumps(data, ensure_ascii=False)

                main_item = {}
                main_item['share_code'] = share_code
                main_item['notice_date'] = notice_date
                main_item['holder_name'] = holder_name
                main_item['pf_org'] = pf_org
                main_item['is_pftype'] = is_pftype
                main_item['pf_num'] = pf_num
                main_item['pf_tsr'] = pf_tsr
                main_item['pf_hold_ratio'] = pf_hold_ratio
                main_item['pf_start_date'] = pf_start_date
                main_item['unfreeze_date'] = unfreeze_date
                main_item['actual_unfreeze_date'] = actual_unfreeze_date
                main_item['unfreeze_state'] = unfreeze_state
                main_item['source'] = source
                main_item['md5_value'] = hash_md5(f"{share_code}:{notice_date}")
                main_item['_table'] = 'listing_stock_pledge'
                main_item['basic_data'] = basic_data
                yield main_item



    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')