import hashlib, scrapy
import math
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.finance.listed_company_eastmoney.fs_key_value import fs_value
from utils.mysql_tools import select_data
from utils.tools import *
from utils.time_kit import *

# https://quote.eastmoney.com/center/gridlist.html#hs_a_board
# 东方财富网-沪深京个股-财务分析-现金流量表
class FinancialAnalysisCashFlowEastmoneySspider(BaseSpider):
    name = 'financial_analysis_cashflow_eastmoney'
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
    def _bare(self, name):
        """去掉显示名的"其中:/加:/减:"前缀，用于分组边界判断。"""
        for p in ('其中:', '加:', '减:'):
            if name.startswith(p):
                return name[len(p):]
        return name

    def _extract_static_names(self, body):
        """解析 staticRenderFns 数组，返回 ({索引: 显示名}, {索引: 是否加粗})。

        Vue 渲染行用 s._m(N) 引用第 N 个静态渲染函数，该函数里 tips-fieldname-Left 的 _v 内容即显示名。
        同时解析 staticClass 是否含 font-bold 标记该行是否加粗标题。
        """
        starts = [m.start() for m in re.finditer(r'=\[function\(\)\{var s=this', body)]
        best = None
        for st in starts:
            lb = body.index('[', st)
            depth = 0
            end = None
            for i in range(lb, min(len(body), lb + 300000)):
                c = body[i]
                if c == '[':
                    depth += 1
                elif c == ']':
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            if end is None:
                continue
            arr = body[lb:end + 1]
            cnt = arr.count('tips-fieldname-Left')
            if best is None or cnt > best[0]:
                best = (cnt, lb, end, arr)

        if best is None:
            return {}, {}

        cnt, lb, end, arr = best
        funcs = []
        depth = 0
        cur = []
        for c in arr[1:-1]:
            if c in '[{(':
                depth += 1
            elif c in ']})':
                depth -= 1
            if c == ',' and depth == 0:
                funcs.append(''.join(cur))
                cur = []
            else:
                cur.append(c)
        if cur:
            funcs.append(''.join(cur))

        names = {}
        bolds = {}
        for idx, fn in enumerate(funcs):
            m = re.search(
                r'staticClass:\s*"tips-fieldname-Left([^"]*)"[^,]*,\s*\[t\("span",\s*\[s\._v\("([^"]+)"\)',
                fn
            )
            if m:
                cls_suffix, name = m.groups()
                names[idx] = name
                bolds[idx] = 'font-bold' in cls_suffix
        return names, bolds

    def extract_cash_flow_with_parent(self):
        """返回列表 [(上一级分类, 科目名, 字段代码, 同比代码), ...]，保持网页显示顺序。"""

        resp = requests.get('https://emweb.securities.eastmoney.com/pc_hsf10/pages/js/chunk-2d0ac05a.f0880539.js', headers=self.headers)
        resp.encoding = "utf-8"
        body = resp.text

        # 解析 staticRenderFns 数组 -> ({索引: 显示名}, {索引: 是否加粗})
        static_names, static_bolds = self._extract_static_names(body)

        # 从渲染行里提取 (显示名, CODE, 函数索引)：changeChartData("_", CODE) 后紧跟 [s._m(N), ...]
        pairs_with_idx = []
        for m in re.finditer(
                r'changeChartData\("([^"]*)",\s*"([A-Z][A-Z0-9_]*)"\)[^\]]{0,200}\[s\._m\((\d+)\)',
                body,
        ):
            cc_name, code, idx_str = m.groups()
            idx = int(idx_str)
            display_name = static_names.get(idx, cc_name)
            pairs_with_idx.append((display_name, code, idx))

        # 解析分组标题及其起始字段
        section_starts = self._parse_section_starts(pairs_with_idx, static_names, static_bolds)

        return self._build_rows(pairs_with_idx, section_starts)

    def _parse_section_starts(self, pairs_with_idx, static_names, static_bolds):
        """从 staticRenderFns 全序列解析分组标题及其"起始数据字段名"。

        逻辑：按 staticRenderFns 索引顺序遍历（即页面渲染顺序），遇到加粗行时：
        - 若该行本身是数据字段（在 pairs 里），分组起点即它自己。
        - 若是纯加粗标题（不在 pairs 里，如"经营活动产生的现金流量"），
          取其后第一个数据字段作为该分组起点。

        Args:
            pairs_with_idx: [(显示名, CODE, staticRenderFns索引), ...]，按页面顺序
            static_names: {索引: 显示名}
            static_bolds: {索引: 是否加粗}

        Returns:
            list[(分组名, 起始字段名)]，按出现顺序。
        """
        # 数据字段名集合（用于判断某行是否有数据）
        data_field_names = {self._bare(name) for name, _, _ in pairs_with_idx}

        section_starts = []
        pending = None
        for idx in sorted(static_names.keys()):
            if not static_bolds.get(idx, False):
                # 非加粗行
                if pending is not None:
                    name = static_names[idx]
                    bare_name = self._bare(name)
                    if bare_name in data_field_names:
                        section_starts.append((pending, bare_name))
                        pending = None
                continue

            # 加粗行
            name = static_names[idx]
            bare_name = self._bare(name)
            if bare_name in data_field_names:
                # 加粗行本身是数据字段
                section_starts.append((name, bare_name))
                pending = None
            else:
                # 纯标题，等后续第一个数据字段
                pending = name

        return section_starts

    def _build_rows(self, pairs_with_idx, section_starts):
        """按数据项顺序输出，遇到某组起点字段就切换上一级分类。"""
        rows = []
        parent = section_starts[0][0] if section_starts else ''
        idx = 0
        for display_name, code, _ in pairs_with_idx:
            bare_name = self._bare(display_name)
            if idx < len(section_starts) and bare_name == section_starts[idx][1]:
                parent = section_starts[idx][0]
                idx += 1
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
            "type": "RPT_F10_FINANCE_GCASHFLOW",
            "sty": "APP_F10_GCASHFLOW",
            "filter": f'(SECUCODE="{code}.{prefix}")',
            "p": "1",
            "ps": "5",
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
                for parent, key, value, yoy in self.cash_flow_sheet_standard:
                    share_code = base_data['code']  # 股票代码
                    main_category = "现金流量表"
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
            "type": "RPT_F10_FINANCE_GCASHFLOWQC",
            "sty": "PC_F10_GCASHFLOWQC",
            "filter": f'(SECUCODE="{code}.{prefix}")',
            "p": "1",
            "ps": "5",
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
                for parent, key, value, yoy in self.cash_flow_sheet_standard:
                    share_code = base_data['code']  # 股票代码
                    main_category = "现金流量表"
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