import hashlib, scrapy
import math
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.finance.listed_company_eastmoney.fs_key_value import fs_value
from utils.mysql_tools import select_data
from utils.tools import *
from utils.time_kit import *

# https://quote.eastmoney.com/center/gridlist.html#hs_a_board
# 东方财富网-沪深京个股-财务分析-资产负债
class FinancialAnalysisLiabilitiesEastmoneySspider(BaseSpider):
    name = 'financial_analysis_liabilities_eastmoney'
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
    def extract_balance_sheet_with_parent(self):
        """返回列表 [(上一级分类, 科目名, 字段代码, 同比代码), ...]，保持网页显示顺序。"""

        resp = common_request('https://emweb.securities.eastmoney.com/pc_hsf10/pages/js/chunk-2d222328.80296733.js', headers=self.headers, proxies_type=True)
        resp.encoding = "utf-8"
        body = resp.text

        # 静态模板里的"其中:"显示名（用于识别缩进子项，如"其中:应收票据"）
        static_names = set()
        for m in re.finditer(r'tips-fieldname-Left[^"]*"\s*\},\s*\[t\("span",\s*\[s\._v\("([^"]+)"\)', body):
            static_names.add(m.group(1))

        # 资产负债表模板段：货币资金 -> 负债和股东权益总计
        seg_start = body.find('"货币资金", "MONETARYFUNDS"')
        if seg_start == -1:
            seg_start = body.find('"货币资金","MONETARYFUNDS"')
        seg_start = max(0, seg_start - 200)
        seg_end = body.find('"负债和股东权益总计", "TOTAL_LIAB_EQUITY"')
        if seg_end == -1:
            seg_end = body.find('"负债和股东权益总计","TOTAL_LIAB_EQUITY"')
        segment = body[seg_start: seg_end + 300]

        # 按 changeChartData 位置切块，逐个提取（名称, 代码, 同比代码, 显示名）
        positions = [m.start() for m in re.finditer(r'changeChartData\(', segment)]
        positions.append(len(segment))

        section_starts = self._parse_section_starts(body)
        return self._build_rows(segment, positions, static_names, section_starts)

    def _parse_section_starts(self, body):
        """从静态模板动态解析分组标题及其下第一个科目名。

        静态模板里每行是 class + 显示名：
          - 分组标题：class 含 font-bold 且名称不含"合计/总计"（流动资产、非流动资产...）
          - 科目行：  class 含 pl20
        取每个分组标题之后紧跟的第一个 pl20 科目名作为该组起点。

        Returns:
            list[(分组名, 该组第一个科目名)]，按出现顺序，只取第一组模板。
        """
        section_starts = []
        pending = None
        for m in re.finditer(
                r'staticClass:\s*"tips-fieldname-Left([^"]*)"\s*\},\s*\[t\("span",\s*\[s\._v\("([^"]+)"\)',
                body,
        ):
            cls, name = m.group(1), m.group(2)
            is_bold = 'font-bold' in cls
            is_total = ('合计' in name) or ('总计' in name)

            if is_bold and not is_total:
                pending = name  # 记住分组标题，等下一个科目
            elif pending is not None and 'pl20' in cls:
                section_starts.append((pending, name))
                pending = None

            if name == '负债和股东权益总计':  # 模板重复多次，只取第一组
                break

        return section_starts

    def _build_rows(self, segment, positions, static_names, section_starts):
        """先按顺序抽出 (显示名, 代码, 同比代码)，再用分组起点科目切换上一级分类。"""
        items = []  # [(display_name, code, yoy_code), ...]
        seen_codes = set()

        for i, pos in enumerate(positions[:-1]):
            block = segment[max(0, pos - 220): positions[i + 1]]

            m_chart = re.search(r'changeChartData\("([^"]+)",\s*"([A-Z][A-Z0-9_]*)"\)', block)
            if not m_chart:
                continue
            chart_name, code = m_chart.group(1), m_chart.group(2)

            if code in seen_codes:  # 跳过新旧准则重复的同一 code
                continue
            seen_codes.add(code)

            # 同比代码：优先读 formatPercent(_.X_YOY)，否则补 _YOY
            m_yoy = re.search(r'formatPercent\(\w+\._([A-Z][A-Z0-9_]*_YOY)\)', block)
            yoy_code = m_yoy.group(1) if m_yoy else code + '_YOY'

            # 显示名：条件渲染的"其中:XXX"优先
            m_cond = re.search(r'\):\s*t\("span",\s*\[s\._v\("([^"]+)"\)\]\)', block)
            if m_cond:
                display_name = m_cond.group(1)
            elif f"其中:{chart_name}" in static_names:
                display_name = f"其中:{chart_name}"
            else:
                display_name = chart_name

            items.append((display_name, code, yoy_code))

        # 用分组起点科目切换上一级分类：数据流里遇到某组的第一个科目名，就切到该组
        rows = []
        parent = section_starts[0][0] if section_starts else ''
        next_idx = 0
        for display_name, code, yoy_code in items:
            # display_name 可能带"其中:"前缀，起点科目名是不带前缀的，故用去前缀名比对
            bare = display_name.split(':', 1)[-1] if display_name.startswith('其中:') else display_name
            if next_idx < len(section_starts) and bare == section_starts[next_idx][1]:
                parent = section_starts[next_idx][0]
                next_idx += 1
            rows.append((parent, display_name, code, yoy_code))

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
        yield from self.get_details({'detail_url': details_url, 'code': code, 'prefix': prefix})

    def get_details(self, data):
        code = data['code']
        prefix = data['prefix']
        url = "https://datacenter.eastmoney.com/securities/api/data/get"
        params = {
            "type": "RPT_F10_FINANCE_GBALANCE",
            "sty": "F10_FINANCE_GBALANCE",
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
            callback=self.parse_details,
            cb_kwargs={'base_data': data}
        )


    def parse_details(self, response, base_data):
        json_data = response.json()
        if json_data['result']:
            for data in json_data['result'].get('data', []):
                for parent, key, value, yoy in self.balance_sheet_standard:
                    share_code = base_data['code']  # 股票代码
                    main_category = "资产负债表"
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



    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')