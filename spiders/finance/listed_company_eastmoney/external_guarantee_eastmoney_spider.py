import hashlib, scrapy
import math
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.finance.listed_company_eastmoney.fs_key_value import fs_value
from utils.mysql_tools import select_data
from utils.tools import *
from utils.time_kit import *


# https://quote.eastmoney.com/center/gridlist.html#hs_a_board
#  公司大事 重大事项 对外担保
class ExternalGuaranteeEastmoneySpider(BaseSpider):
    name = 'external_guarantee_eastmoney'
    data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 8, 'DOWNLOAD_DELAY': 0.5,
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
        details_url = f"https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code={prefix}{code}&color=b#/gsds"
        yield from self.get_details({'detail_url': details_url, 'code': code, 'prefix': prefix})

    def get_details(self, data):
        code = data['code']
        prefix = data['prefix']
        url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        params = {
            "reportName": "RPT_F10_ORGRES_GUARANTEE",
            "columns": "ALL",
            "quoteColumns": "",
            "filter": f'(SECUCODE="{code}.{prefix}")',
            "pageNumber": "1",
            "pageSize": "100",
            "sortTypes": "-1",
            "sortColumns": "NOTICE_DATE",
            "source": "HSF10",
            "client": "PC",
            "v": "07126657229405229"
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
                notice_date = data['NOTICE_DATE']   # 公告日期
                guar_name = data['GUAR_NAME']   # 担保方
                guaranteed_name = data['GUARANTEED_NAME']   # 被担保方
                guarantee_way = data['GUARANTEE_WAY']   # 担保方式
                guarantee_amt = data['GUARANTEE_AMT']   # 担保金额(万元)
                currency = data['CURRENCY']   # 币种
                guarantee_expire = data['GUARANTEE_EXPIRE']   # 担保期限(年)
                guarantee_start_date = data['GUARANTEE_START_DATE']   # 担保起始日
                guarantee_end_date = data['GUARANTEE_END_DATE']   # 担保终止日
                is_perform = data['IS_PERFORM']   # 是否履行完毕
                is_related_trade = data['IS_RELATED_TRADE']   # 是否关联交易
                trade_date = data['TRADE_DATE']   # 交易日期
                guar_event_explain = data['GUAR_EVENT_EXPLAIN']   # 担保事件说明
                report_date = data['REPORT_DATE']   # 报告期
                report_type_name = data['REPORT_TYPE_NAME']   # 报告期类别
                source = base_data['detail_url']    # 来源网址
                basic_data = json.dumps(data, ensure_ascii=False)

                main_item = {}
                main_item['share_code'] = share_code
                main_item['notice_date'] = notice_date
                main_item['guar_name'] = guar_name
                main_item['guaranteed_name'] = guaranteed_name
                main_item['guarantee_way'] = guarantee_way
                main_item['guarantee_amt'] = guarantee_amt
                main_item['currency'] = currency
                main_item['guarantee_expire'] = guarantee_expire
                main_item['guarantee_start_date'] = guarantee_start_date
                main_item['guarantee_end_date'] = guarantee_end_date
                main_item['is_perform'] = is_perform
                main_item['is_related_trade'] = is_related_trade
                main_item['trade_date'] = trade_date
                main_item['guar_event_explain'] = guar_event_explain
                main_item['report_date'] = report_date
                main_item['report_type_name'] = report_type_name
                main_item['source'] = source
                main_item['md5_value'] = hash_md5(f"{share_code}:{notice_date}")
                main_item['_table'] = 'listing_stock_guarantee'
                main_item['basic_data'] = basic_data

                yield main_item



    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')