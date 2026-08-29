import hashlib, scrapy
import math
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.finance.listed_company_eastmoney.fs_key_value import fs_value
from utils.mysql_tools import select_data
from utils.tools import *
from utils.time_kit import *

# https://quote.eastmoney.com/center/gridlist.html#hs_a_board
# 东方财富网-沪深京个股-财务分析-利润表
class FinancialAnalysisProfitEastmoneySspider(BaseSpider):
    name = 'financial_analysis_profit_eastmoney'
    data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
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

    # 以下为找字段映射关系

    # 显示名前缀（模板里有，changeChartData 名字里没有）
    _PREFIXES = ('其中:', '加:', '减:')
    def _bare(self, name):
        """去掉显示名的"其中:/加:/减:"前缀，用于和 changeChartData 名字比对。"""
        for p in self._PREFIXES:
            if name.startswith(p):
                return name[len(p):]
        return name

    def extract_income_statement_with_parent(self):
        """返回列表 [(上一级分类, 科目名, 字段代码, 同比代码), ...]，保持网页显示顺序。"""

        resp = common_request('https://emweb.securities.eastmoney.com/pc_hsf10/pages/js/chunk-2d21f210.06f0c723.js', headers=self.headers, proxies_type=True)
        resp.encoding = "utf-8"
        body = resp.text

        # changeChartData 列表就是页面权威顺序 [(name, code), ...]
        cc = re.findall(r'changeChartData\("([^"]+)",\s*"([A-Z][A-Z0-9_]*)"\)', body)

        # 模板行（class 后缀, 显示名），用于解析分组标题与显示名前缀
        tmpl = self._parse_template_rows(body)

        section_starts = self._parse_section_starts(tmpl, {n for n, _ in cc})
        display_map = self._build_display_map(tmpl)  # bare name -> 带前缀显示名

        return self._build_rows(cc, section_starts, display_map)

    def _parse_template_rows(self, body):
        """按出现顺序解析静态模板行，返回 [(class后缀, 显示名), ...]（只取第一组模板）。"""
        rows = []
        for cls, name in re.findall(
                r'staticClass:\s*"tips-fieldname-Left([^"]*)"[^,]*,\s*\[t\("span",\s*\[s\._v\("([^"]+)"\)',
                body,
        ):
            rows.append((cls.strip(), name))
            if name == '综合收益总额':  # 模板重复多次，只取第一组
                break
        return rows

    def _parse_section_starts(self, tmpl, cc_names):
        """从模板动态解析分组标题及其"起始数据字段名"。

        - 加粗标题（font-bold）本身若是数据字段（如"营业总收入"），起点即它自己。
        - 否则（纯标题，如"其他经营收益"），取其后第一个属于数据字段的行作为起点。

        Returns:
            list[(分组名, 起始字段名)]，按出现顺序。
        """
        section_starts = []
        pending = None
        for cls, name in tmpl:
            if 'font-bold' in cls:
                pending = name
                if self._bare(name) in cc_names:
                    section_starts.append((name, self._bare(name)))
                    pending = None
            elif pending is not None and self._bare(name) in cc_names:
                section_starts.append((pending, self._bare(name)))
                pending = None
        return section_starts

    def _build_display_map(self, tmpl):
        """bare 名 -> 带前缀显示名（仅记录带前缀的，用于还原"其中:/加:/减:"）。"""
        display_map = {}
        for _, name in tmpl:
            if name.startswith(self._PREFIXES):
                display_map.setdefault(self._bare(name), name)
        return display_map

    def _build_rows(self, cc, section_starts, display_map):
        """按 changeChartData 顺序输出，遇到某组起点字段就切换上一级分类。"""
        rows = []
        parent = section_starts[0][0] if section_starts else ''
        idx = 0
        for name, code in cc:
            if idx < len(section_starts) and name == section_starts[idx][1]:
                parent = section_starts[idx][0]
                idx += 1
            display_name = display_map.get(name, name)
            rows.append((parent, display_name, code, code + '_YOY'))
        return rows
    # 以上为找字段映射关系

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
            "type": "RPT_F10_FINANCE_GINCOME",
            "sty": "APP_F10_GINCOME",
            "filter": f'(SECUCODE="{code}.{prefix}")',
            "p": "1",
            "ps": "50",
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
                for parent, key, value, yoy in self.profit_sheet_standard:
                    share_code = base_data['code']  # 股票代码
                    main_category = "利润表"
                    subcategory = '按报告期'
                    publish_date = data['REPORT_DATE'].split(' ')[0]    # 日期
                    parent = parent     # 父类
                    channel = f"{key}(元)"   # 字段名称
                    content = data.get(value)   # 字段值
                    source = base_data['detail_url']    # 来源网址

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
        url = "https://datacenter.eastmoney.com/securities/api/data/get"
        params = {
            "type": "RPT_F10_FINANCE_GINCOMEQC",
            "sty": "PC_F10_GINCOMEQC",
            "filter": f'(SECUCODE="{code}.{prefix}")',
            "p": "1",
            "ps": "50",
            "sr": "-1",
            "st": "REPORT_DATE",
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
                for parent, key, value, yoy in self.profit_sheet_standard:
                    share_code = base_data['code']  # 股票代码
                    main_category = "利润表"
                    subcategory = '按单季度'
                    publish_date = data['REPORT_DATE'].split(' ')[0]    # 日期
                    parent = parent     # 父类
                    channel = f"{key}(元)"   # 字段名称
                    content = data.get(value)   # 字段值
                    source = base_data['detail_url']    # 来源网址

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