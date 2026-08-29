import hashlib, scrapy
import math
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.finance.listed_company_eastmoney.fs_key_value import fs_value
from utils.mysql_tools import select_data
from utils.tools import *
from utils.time_kit import *

# https://quote.eastmoney.com/center/gridlist.html#hs_a_board
# 东方财富网-沪深京个股-财务分析-主要指标
class FinancialAnalysisMainEastmoneySpider(BaseSpider):
    name = 'financial_analysis_main_eastmoney'
    data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 5, 'DOWNLOAD_DELAY': 1,
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

    # self.report_name_key = {
    #     # 每股指标
    #     '基本每股收益(元)': 'EPSJB',
    #     '扣非每股收益(元)': 'EPSKCJB',
    #     '稀释每股收益(元)': 'EPSXS',
    #     '每股净资产(元)': 'BPS',
    #     '每股公积金(元)': 'MGZBGJ',
    #     '每股未分配利润(元)': 'MGWFPLR',
    #     '每股经营现金流(元)': 'MGJYXJJE',
    #     # 成长能力指标
    #     '营业总收入(元)': 'TOTALOPERATEREVE',
    #     '毛利润(元)': 'MLR',
    #     '归属净利润(元)': 'PARENTNETPROFIT',
    #     '扣非净利润(元)': 'KCFJCXSYJLR',
    #     '营业总收入同比增长(%)': 'TOTALOPERATEREVETZ',
    #     '归属净利润同比增长(%)': 'PARENTNETPROFITTZ',
    #     '扣非净利润同比增长(%)': 'KCFJCXSYJLRTZ',
    #     '营业总收入滚动环比增长(%)': 'YYZSRGDHBZC',
    #     '归属净利润滚动环比增长(%)': 'NETPROFITRPHBZC',
    #     '扣非净利润滚动环比增长(%)': 'KFJLRGDHBZC',
    #     # 盈利能力指标
    #     '净资产收益率(加权)(%)': 'ROEJQ',
    #     '净资产收益率(扣非/加权)(%)': 'ROEKCJQ',
    #     '总资产收益率(加权)(%)': 'ZZCJLL',
    #     '毛利率(%)': 'XSMLL',
    #     '净利率(%)': 'XSJLL',
    #     # 收益质量指标
    #     '预收账款/营业收入': 'YSZKYYSR',
    #     '销售净现金流/营业收入': 'XSJXLYYSR',
    #     '经营净现金流/营业收入': 'JYXJLYYSR',
    #     '实际税率(%)': 'TAXRATE',
    #     # 财务风险指标
    #     '流动比率': 'LD',
    #     '速动比率': 'SD',
    #     '现金流量比率': 'XJLLB',
    #     '资产负债率(%)': 'ZCFZL',
    #     '权益系数': 'QYCS',
    #     '产权比率': 'CQBL',
    #     # 营运能力指标
    #     '总资产周转天数(天)': 'ZZCZZTS',
    #     '存货周转天数(天)': 'CHZZTS',
    #     '应收账款周转天数(天)': 'YSZKZZTS',
    #     '总资产周转率(次)': 'TOAZZL',
    #     '存货周转率(次)': 'CHZZL',
    #     '应收账款周转率(次)': 'YSZKZZL',
    # }
    # self.quarter_name_key = {
    #     # 每股指标
    #     '摊薄每股收益(元)': 'EPSJB',
    #     '每股经营现金流(元)': 'PER_NETCASH',
    #     # 成长能力指标
    #     '营业总收入(元)': 'TOTALOPERATEREVE',
    #     '毛利润(元)': 'GROSS_PROFIT',
    #     '归属净利润(元)': 'PARENTNETPROFIT',
    #     '扣非净利润(元)': 'DEDU_PARENT_PROFIT',
    #     '营业总收入同比增长(%)': 'TOTALOPERATEREVETZ',
    #     '归属净利润同比增长(%)': 'PARENTNETPROFITTZ',
    #     '扣非净利润同比增长(%)': 'DPNP_YOY_RATIO',
    #     '营业总收入滚动环比增长(%)': 'YYZSRGDHBZC',
    #     '归属净利润滚动环比增长(%)': 'NETPROFITRPHBZC',
    #     '扣非净利润滚动环比增长(%)': 'KFJLRGDHBZC',
    #     # 盈利能力指标
    #     '摊薄净资产收益率(%)': '',
    #     '摊薄总资产收益率(%)': '',
    #     '毛利率(%)': '',
    #     '净利率(%)': '',
    # }
    main_name_key = {}

    def extract_main_indicators(self):
        """按 JS 渲染顺序动态提取分组后的字段列表。

        返回格式：[(分组名, 指标名, 字段代码), ...]
        分组名直接来自 JS 里的标题行文本（每股指标 / 成长能力指标 / … / 专项指标）。
        """

        # 分组标题行：a("tr",{staticClass:"title"},[a("td",...[t._v("分组名")])
        _TITLE_RE = re.compile(r'staticClass:"title"[^\]]*?t\._v\("([^"]+)"\)')

        # 数据行：a("td",[t._v("指标名")]),t._l(t.displayList,(function(e,s){return a("td",{key:s},[t._v(t._s(t.common.XXX(e.CODE
        _DATA_RE = re.compile(
            r'a\("td",\[t\._v\("([^"]+)"\)\]\),'
            r't\._l\(t\.displayList,\(function\(e,s\)\{return a\("td",\{key:s\},'
            r'\[t\._v\(t\._s\(t\.common\.[a-zA-Z]+\(e\.([A-Z0-9_]+)'
        )

        # 标题行渲染日期占位（REPORT_DATE）等非指标代码
        _SKIP_CODES = {'REPORT_DATE', 'YEAR', 'ITEM_NAME'}

        resp = common_request('https://emweb.securities.eastmoney.com/pc_hsf10/pages/js/chunk-0389df4c.79480089.js', headers=self.headers, proxies_type=True)
        resp.encoding = "utf-8"
        body = resp.text

        # 汇总标题事件与数据事件，按在文档中的位置排序，模拟页面渲染顺序
        events = []
        for m in _TITLE_RE.finditer(body):
            events.append((m.start(), 'TITLE', m.group(1).strip(), None))
        for m in _DATA_RE.finditer(body):
            name, code = m.group(1).strip(), m.group(2)
            if code in _SKIP_CODES:
                continue
            events.append((m.start(), 'DATA', name, code))
        events.sort(key=lambda e: e[0])

        rows = []
        seen = set()
        current_group = '未分组'
        for _pos, kind, name, code in events:
            if kind == 'TITLE':
                current_group = name
                continue
            # 跳过标题行本身被数据正则命中的情况（指标名 == 当前分组名）
            if name == current_group:
                continue
            if code in seen:
                continue
            seen.add(code)
            rows.append((current_group, name, code))
        return rows

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
        details_url = f"https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code={prefix}{code}&color=b#/cwfx"
        yield from self.get_report_details({'detail_url': details_url, 'code': code, 'prefix': prefix})
        yield from self.get_quarter_details({'detail_url': details_url, 'code': code, 'prefix': prefix})

    def get_report_details(self, data):
        code = data['code']
        prefix = data['prefix']
        url = "https://datacenter.eastmoney.com/securities/api/data/get"
        params = {
            "type": "RPT_F10_FINANCE_MAINFINADATA",
            "sty": "APP_F10_MAINFINADATA",
            "quoteColumns": "",
            "filter": f'(SECUCODE="{code}.{prefix}")',
            "p": "1",
            "ps": "200",
            "sr": "-1",
            "st": "REPORT_DATE",
            "source": "HSF10",
            "client": "PC",
            "v": ""
        }
        yield scrapy.Request(
            url=f"{url}?{urlencode(params)}",
            headers=self.headers,
            callback=self.parse_report_details,
            cb_kwargs={'base_data': data}
        )

    def parse_report_details(self, response, base_data):
        json_data = response.json()
        if json_data['result']:
            for data in json_data['result'].get('data', []):
                for parent, key, value in self.main_name_key:
                    share_code = base_data['code']
                    main_category = "主要指标"
                    subcategory = '按报告期'
                    publish_date = data['REPORT_DATE'].split(' ')[0]
                    parent = parent
                    channel = key
                    content = data.get(value)
                    source = base_data['detail_url']

                    main_item = {}
                    main_item['share_code'] = share_code
                    main_item['main_category'] = main_category
                    main_item['subcategory'] = subcategory
                    main_item['publish_date'] = publish_date
                    main_item['parent'] = parent
                    main_item['channel'] = channel
                    main_item['content'] = content
                    main_item['source'] = source
                    main_item['md5_value'] = hash_md5(f"{share_code}{main_category}{subcategory}{publish_date}{parent}{channel}")
                    # insert_data('listing_stock_finance', main_item)
                    main_item['_table'] = 'listing_stock_finance'
                    yield main_item


    def get_quarter_details(self, data):
        code = data['code']
        prefix = data['prefix']
        url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        params = {
            "reportName": "RPT_F10_QTR_MAINFINADATA",
            "columns": "ALL",
            "quoteColumns": "",
            "filter": f'(SECUCODE="{code}.{prefix}")',
            "pageNumber": "1",
            "pageSize": "200",
            "sortTypes": "-1",
            "sortColumns": "REPORT_DATE",
            "source": "HSF10",
            "client": "PC",
            "v": ""
        }
        yield scrapy.Request(
            url=f"{url}?{urlencode(params)}",
            headers=self.headers,
            callback=self.parse_quarter_details,
            cb_kwargs={'base_data': data}
        )

    def parse_quarter_details(self, response, base_data):
        json_data = response.json()
        if json_data['result']:
            for data in json_data['result'].get('data', []):
                for parent, key, value in self.main_name_key:
                    share_code = base_data['code']
                    main_category = "主要指标"
                    subcategory = '按单季度'
                    parent = parent
                    publish_date = data['REPORT_DATE'].split(' ')[0]
                    channel = key
                    content = data.get(value)
                    source = base_data['detail_url']

                    main_item = {}
                    main_item['share_code'] = share_code
                    main_item['main_category'] = main_category
                    main_item['subcategory'] = subcategory
                    main_item['publish_date'] = publish_date
                    main_item['parent'] = parent
                    main_item['channel'] = channel
                    main_item['content'] = content
                    main_item['source'] = source
                    main_item['md5_value'] = hash_md5(f"{share_code}{main_category}{subcategory}{publish_date}{parent}{channel}")
                    # insert_data('listing_stock_finance', main_item)
                    main_item['_table'] = 'listing_stock_finance'
                    yield main_item

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')