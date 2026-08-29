"""
AMAC 基金公示爬虫（中国证券投资基金协会 gs.amac.org.cn）
覆盖 11 张数据表：

  private_fund_manager              — 私募基金管理人
  private_fund_products             — 私募基金产品
  securities_company_product        — 证券公司集合资管产品
  securities_company_direct_investment_fund — 证券公司直投基金
  securities_private_equity_fund    — 证券公司私募投资基金（含基金公司）
  subsidiary_aggregate_product      — 基金公司及子公司集合资管产品
  asset_backed_plan                 — 资产支持专项计划
  futures_products                  — 期货公司集合资管产品
  member_mechanism                  — 会员机构
  private_fund_register_process     — 私募基金管理人登记办理流程公示
  cancel_the_fund_manager           — 已注销私募基金管理人公示

增量策略：
  start_page=1 end_page=2（各接口前2页）
  去重字段：md5_value

本地调试：
  scrapy crawl economy_amac_fund -a start_page=1 -a end_page=2
  scrapy crawl economy_amac_fund -a start_page=1 -a end_page=2 -a target=private_fund_manager
"""
import hashlib
import json
import time
import random
from datetime import datetime

import scrapy
from lxml import etree

from spiders.base_spider import BaseSpider

_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0'
)

_HDRS = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Origin': 'https://gs.amac.org.cn',
    'Referer': 'https://gs.amac.org.cn/',
    'User-Agent': _UA,
}

_HDRS_HTML = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://gs.amac.org.cn/',
    'User-Agent': _UA,
}

def _md5(*parts) -> str:
    return hashlib.md5(''.join(str(p or '') for p in parts).encode()).hexdigest()

def _ts(ts, divisor=1000):
    """timestamp(ms) → yyyy-MM-dd"""
    if not ts:
        return ''
    try:
        return time.strftime('%Y-%m-%d', time.localtime(int(ts) / divisor))
    except Exception:
        try:
            return time.strftime('%Y-%m-%d', time.localtime(int(ts) / 100000))
        except Exception:
            return ''

def _txt(node_list):
    if node_list:
        return node_list[0].strip().replace('\n', '').replace('\xa0', '').replace(' ', '')
    return ''

class AmacFundSpider(BaseSpider):
    # 项目早已经拆分，且停止这个任务

    """AMAC 基金公示系列爬虫（11 张表合并）"""

    name         = 'economy_amac_fund'
    data_table   = 'private_fund_manager'
    dedup_fields = ['md5_value']

    allowed_domains = ['gs.amac.org.cn']
    default_end_page = 2

    proxy_type = 'long_proxy'

    custom_settings = {
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
    }

    # ------------------------------------------------------------------ #
    # start_requests                                                       #
    # ------------------------------------------------------------------ #
    def start_requests(self):
        target = getattr(self, 'target', 'all')

        r = random.random()
        targets = {
            # table_name: (url_template, callback, page_base)
            # page_base=0: page 从 0 开始; page_base=1: pageNo 从 1 开始
            'private_fund_manager': (
                'https://gs.amac.org.cn/amac-infodisc/api/pof/manager/query?&page={p}&size=20',
                self._parse_manager_list, 0,
            ),
            'private_fund_products': (
                f'https://gs.amac.org.cn/amac-infodisc/api/pof/fund?rand={r}&pageNo={{p}}&pageSize=20',
                self._parse_fund_list, 1,
            ),
            'securities_company_product': (
                f'https://gs.amac.org.cn/amac-infodisc/api/pof/securities?rand={r}&pageNo={{p}}&pageSize=20',
                self._parse_securities_product, 1,
            ),
            'securities_company_direct_investment_fund': (
                f'https://gs.amac.org.cn/amac-infodisc/api/aoin/product?rand={r}&pageNo={{p}}&pageSize=20',
                self._parse_direct_investment_list, 1,
            ),
            'securities_private_equity_fund': (
                f'https://gs.amac.org.cn/amac-infodisc/api/pof/subfund?rand={r}&pageNo={{p}}&pageSize=20',
                self._parse_subfund, 1,
            ),
            'subsidiary_aggregate_product': (
                f'https://gs.amac.org.cn/amac-infodisc/api/fund/account?rand={r}&pageNo={{p}}&pageSize=20',
                self._parse_aggregate_list, 1,
            ),
            'asset_backed_plan': (
                f'https://gs.amac.org.cn/amac-infodisc/api/fund/abs?rand={r}&pageNo={{p}}&pageSize=20',
                self._parse_abs, 1,
            ),
            'futures_products': (
                f'https://gs.amac.org.cn/amac-infodisc/api/pof/futures?rand={r}&pageNo={{p}}&pageSize=20',
                self._parse_futures, 1,
            ),
            'member_mechanism': (
                f'https://gs.amac.org.cn/amac-infodisc/api/pof/pofMember?rand={r}&pageNo={{p}}&pageSize=20',
                self._parse_member_list, 1,
            ),
            'private_fund_register_process': (
                f'https://gs.amac.org.cn/amac-infodisc/api/pof/manager/register-flow?rand={r}&pageNo={{p}}&pageSize=20',
                self._parse_register_flow, 1,
            ),
            # cancel_the_fund_manager: 接口目前被 WAF 拦截（400），暂时跳过
        }

        for tbl, (url_tpl, cb, base) in targets.items():
            if target != 'all' and target != tbl:
                continue
            for page in range(self.start_page - 1 + base, self.end_page + base):
                yield scrapy.Request(
                    url=url_tpl.format(p=page),
                    method='POST',
                    body='{}',
                    headers=_HDRS,
                    callback=cb,
                    errback=self.errback,
                    meta={'table': tbl, 'page': page},
                )

    # ------------------------------------------------------------------ #
    # 私募基金管理人（private_fund_manager）                               #
    # 列表仅获取基本字段，详情页通过 HTML 解析补全                         #
    # ------------------------------------------------------------------ #
    def _parse_manager_list(self, response):
        try:
            data = response.json()
            rows = data.get('content') or []
        except Exception:
            return
        for row in rows:
            manager_name = row.get('managerName', '')
            reg_no       = row.get('registerNo', '')
            if not manager_name:
                continue
            fund_url = 'https://gs.amac.org.cn/amac-infodisc/res/pof/manager/' + (row.get('url') or '')
            yield scrapy.Request(
                url=fund_url,
                headers=_HDRS_HTML,
                callback=self._parse_manager_detail,
                errback=self.errback,
                meta={
                    'manager_name': manager_name,
                    'legal_person': row.get('artificialPersonName'),
                    'organization_type': row.get('primaryInvestType'),
                    'registration_number': reg_no,
                    'registration_location': row.get('regAdrAgg'),
                    'office_location': row.get('officeAdrAgg'),
                    'founded_date': _ts(row.get('establishDate')),
                    'registration_date': _ts(row.get('registerDate')),
                    'fund_number': row.get('fundCount'),
                    'personnel_type': row.get('memberType'),
                    'is_tip_info': '是' if row.get('hasSpecialTips') else '否',
                    'is_faith_info': '是' if row.get('hasCreditTips') else '否',
                    'fund_url': fund_url,
                },
            )

    def _parse_manager_detail(self, response):
        meta = response.meta
        try:
            tree = etree.HTML(response.body)
        except Exception:
            return

        def _row(tr_list, idx):
            try:
                return _txt(tr_list[idx].xpath('./td[2]/text()'))
            except Exception:
                return ''

        # 机构信息 table
        tr = tree.xpath('//div[@class="info-body"]/div[2]/div[@class="table-response"]/table/tbody/tr')
        fund_size             = _txt(tree.xpath('//div[@class="info-body"]/div[2]/div[2]/table/tbody/tr[last()-1]/td[2]/text()'))
        org_code              = _row(tr, 3)
        registered_capital    = _row(tr, 8)
        paid_in               = _row(tr, 9)
        registration_ratio    = _row(tr, 10)
        enterprise_nature     = _row(tr, 11)
        business_type         = _row(tr, 13)
        full_time_staff       = _row(tr, 14)
        num_fund_members      = _row(tr, 15)
        inst_update_time      = _row(tr, 18) or _row(tr, 17)

        # 会员信息
        mem = tree.xpath('//div[@class="info-body"]/div[3]/div[@class="table-response"]/table/tbody/tr')
        is_member = member_rep = member_type = membership_time = ''
        if mem:
            is_member   = _txt(mem[0].xpath('./td[2]/text()'))
            member_rep  = _txt(mem[0].xpath('./td[4]/text()'))
            if len(mem) > 1:
                member_type     = _txt(mem[1].xpath('./td[2]/text()'))
                membership_time = _txt(mem[1].xpath('./td[4]/text()'))

        # 法律意见书
        law = tree.xpath('//div[@class="info-body"]/div[4]/div[@class="table-response"]/table/tbody/tr')
        legal_op_status = law_firm_name = lawyer_name = ''
        if law:
            legal_op_status = _txt(law[0].xpath('./td[2]/text()'))
            if len(law) > 1:
                law_firm_name = _txt(law[1].xpath('./td[2]/text()'))
                lawyer_name   = _txt(law[1].xpath('./td[4]/text()'))

        # 高管
        exec_trs = tree.xpath('//div[@class="info-body"]/div[6]/div[@class="table-response"]/table/tbody/tr')
        exec_info = []
        for i in range(0, len(exec_trs), 3):
            try:
                exec_info.append({
                    'post': _txt(exec_trs[i].xpath('./td[2]/text()')),
                    'name': _txt(exec_trs[i].xpath('./td[4]/text()')),
                    'is_qualifications': _txt(exec_trs[i+1].xpath('./td[2]/text()')),
                    'acquisition_method': _txt(exec_trs[i+1].xpath('./td[4]/text()')),
                })
            except Exception:
                break

        # 关联方
        related_trs = tree.xpath('//div[@class="info-body"]/div[7]/div[@class="table-response"]/table/tbody/tr/td[2]/table/tbody/tr')
        related_info = [{'name': _txt(r.xpath('./td[3]/a/text()')), 'type': _txt(r.xpath('./td[2]/text()'))} for r in related_trs]

        # 出资人
        investor_trs = tree.xpath('//div[@class="info-body"]/div[8]/div[@class="table-response"]/table/tbody/tr/td[2]/table/tbody/tr')
        investor_info = [{'name': _txt(r.xpath('./td[2]/text()')), 'ratio': _txt(r.xpath('./td[3]/text()'))} for r in investor_trs]

        item = {}
        item['spider_name']               = self.name
        item['_table']             = 'private_fund_manager'
        item['manager_name']              = meta['manager_name']
        item['legal_person']              = meta['legal_person']
        item['organization_type']         = meta['organization_type']
        item['registration_number']       = meta['registration_number']
        item['registration_location']     = meta['registration_location']
        item['office_location']           = meta['office_location']
        item['founded_date']              = meta['founded_date']
        item['registration_date']         = meta['registration_date']
        item['fund_number']               = meta['fund_number']
        item['personnel_type']            = meta['personnel_type']
        item['is_tip_info']               = meta['is_tip_info']
        item['is_faith_info']             = meta['is_faith_info']
        item['fund_url']                  = meta['fund_url']
        item['fund_size']                 = fund_size
        item['filing_date']               = None
        item['fund_status']               = None
        item['Organizational_code']       = org_code
        item['registered_capital']        = registered_capital
        item['Paid_in']                   = paid_in
        item['Registration_ratio']        = registration_ratio
        item['Enterprise_nature']         = enterprise_nature
        item['Business_type']             = business_type
        item['Full_time_staff']           = full_time_staff
        item['Number_of_Fund_Members']    = num_fund_members
        item['Institutional_update_time'] = inst_update_time
        item['is_member']                 = is_member
        item['Member_representative']     = member_rep
        item['Member_type']               = member_type
        item['Membership_time']           = membership_time
        item['Legal_Opinion_Status']      = legal_op_status
        item['Name_of_Law_Firm']          = law_firm_name
        item['lawyer_name']               = lawyer_name
        item['Executive_Information']     = json.dumps(exec_info, ensure_ascii=False)
        item['Related_party_information'] = json.dumps(related_info, ensure_ascii=False)
        item['Investor_Information']      = json.dumps(investor_info, ensure_ascii=False)
        item['Product_Information']       = None
        item['Reminder_information']      = None
        item['md5_value']                 = _md5(meta['manager_name'], meta['registration_number'])
        yield item

    # ------------------------------------------------------------------ #
    # 私募基金产品（private_fund_products）                                #
    # ------------------------------------------------------------------ #
    def _parse_fund_list(self, response):
        try:
            rows = response.json().get('content') or []
        except Exception:
            return
        for row in rows:
            fund_url = 'https://gs.amac.org.cn/amac-infodisc/res/pof/fund/' + (row.get('url') or '')
            yield scrapy.Request(
                url=fund_url,
                headers=_HDRS_HTML,
                callback=self._parse_fund_detail,
                errback=self.errback,
                meta={'fund_url': fund_url},
            )

    def _parse_fund_detail(self, response):
        fund_url = response.meta['fund_url']
        try:
            tree = etree.HTML(response.body)
        except Exception:
            return
        tr_list = tree.xpath('//div[@class="info-body"]/div[1]/div[@class="table-response"]/table/tbody/tr')
        field_map = {
            '基金名称': 'fund_name',
            '基金管理人名称': 'manager_name',
            '托管人名称': 'legal_person',
            '成立时间': 'founded_date',
            '备案时间': 'registration_date',
            '基金类型': 'proficient_type',
            '基金编号': 'fund_number',
            '运作状态': 'fund_state',
            '基金信息最后更新时间': 'last_updatetime',
            '管理类型': 'administration_type',
        }
        result = {v: '' for v in field_map.values()}
        for tr in tr_list:
            title = _txt(tr.xpath('./td[1]/text()'))
            for k, v in field_map.items():
                if k in title:
                    result[v] = _txt(tr.xpath('./td[2]/text()')) or _txt(tr.xpath('./td[2]/a/text()'))
                    break

        fund_name = result['fund_name']
        if not fund_name:
            return

        item = {}
        item['spider_name']          = self.name
        item['_table']             = 'private_fund_products'
        item['fund_name']            = fund_name
        item['manager_name']         = result['manager_name']
        item['legal_person']         = result['legal_person']
        item['founded_date']         = result['founded_date']
        item['registration_date']    = result['registration_date']
        item['fund_series']          = None
        item['fund_size']            = None
        item['fund_count']           = None
        item['proficient_type']      = result['proficient_type']
        item['business_full_name']   = None
        item['investment_mechanism_id'] = None
        item['investment_mechanism'] = None
        item['fund_number']          = result['fund_number']
        item['fund_state']           = result['fund_state']
        item['fund_url']             = fund_url
        item['last_updatetime']      = result['last_updatetime']
        item['administration_type']  = result['administration_type']
        item['md5_value']            = _md5(fund_name, result['fund_number'])
        yield item

    # ------------------------------------------------------------------ #
    # 证券公司集合资管产品（securities_company_product）                   #
    # ------------------------------------------------------------------ #
    def _parse_securities_product(self, response):
        try:
            rows = response.json().get('content') or []
        except Exception:
            return
        for row in rows:
            product_name = row.get('cpmc', '')
            product_code = row.get('cpbm', '')
            if not product_name:
                continue
            item = {}
            item['spider_name']            = self.name
            item['_table']             = 'securities_company_product'
            item['product_name']           = product_name
            item['product_code']           = product_code
            item['administrator_name']     = row.get('gljg')
            item['custodian_name']         = row.get('tgjg')
            item['filing_date']            = row.get('barq')
            item['establish_date']         = row.get('slrq')
            item['due_date']               = row.get('dqr')
            item['investment_type']        = row.get('tzlx')
            item['whether_classification'] = row.get('sffj')
            item['operation_status']       = row.get('yzzt')
            item['fund_url']               = f"https://gs.amac.org.cn/amac-infodisc/res/pof/securities/detail.html?id={row.get('id', '')}"
            item['md5_value']              = _md5(product_name, product_code)
            yield item

    # ------------------------------------------------------------------ #
    # 证券公司直投基金（securities_company_direct_investment_fund）         #
    # ------------------------------------------------------------------ #
    def _parse_direct_investment_list(self, response):
        try:
            rows = response.json().get('content') or []
        except Exception:
            return
        for row in rows:
            detail_url = f"https://gs.amac.org.cn/amac-infodisc/res/aoin/product/{row.get('id', '')}.html"
            yield scrapy.Request(
                url=detail_url,
                headers=_HDRS_HTML,
                callback=self._parse_direct_investment_detail,
                errback=self.errback,
                meta={'fund_url': detail_url},
            )

    def _parse_direct_investment_detail(self, response):
        fund_url = response.meta['fund_url']
        try:
            tree = etree.HTML(response.body)
        except Exception:
            return
        tr_list = tree.xpath('//div[@class="info-body"]/div[1]/div[@class="table-response"]/table/tbody/tr')
        field_map = {
            '产品名称': 'product_name',
            '产品编码': 'product_code',
            '直投子公司名称': 'direct_investment_subsidiary',
            '管理机构名称': 'administration_mechanism',
            '设立日期': 'establishment_date',
            '备案日期': 'filing_date',
            '基金类型': 'fund_type',
            '组织形式': 'organizational_form',
            '运作状态': 'operation_status',
            '是否托管': 'whether_trusteeship',
            '托管人名称': 'trusteeship_name',
        }
        result = {v: '' for v in field_map.values()}
        for tr in tr_list:
            title = _txt(tr.xpath('./td[@class="title"]/text()'))
            for k, v in field_map.items():
                if k in title:
                    result[v] = _txt(tr.xpath('./td[2]/text()'))
                    break

        product_name = result['product_name']
        product_code = result['product_code']
        if not product_name:
            return

        item = {}
        item['spider_name']                  = self.name
        item['_table']             = 'securities_company_direct_investment_fund'
        item['product_name']                 = product_name
        item['product_code']                 = product_code
        item['direct_investment_subsidiary'] = result['direct_investment_subsidiary']
        item['administration_mechanism']     = result['administration_mechanism']
        item['establishment_date']           = result['establishment_date']
        item['filing_date']                  = result['filing_date']
        item['fund_type']                    = result['fund_type']
        item['organizational_form']          = result['organizational_form']
        item['operation_status']             = result['operation_status']
        item['whether_trusteeship']          = result['whether_trusteeship']
        item['trusteeship_name']             = result['trusteeship_name']
        item['fund_url']                     = fund_url
        item['md5_value']                    = _md5(product_name, product_code)
        yield item

    # ------------------------------------------------------------------ #
    # 证券公司/基金公司私募投资基金（securities_private_equity_fund）       #
    # ------------------------------------------------------------------ #
    def _parse_subfund(self, response):
        try:
            rows = response.json().get('content') or []
        except Exception:
            return
        for row in rows:
            product_name = row.get('productName', '')
            product_code = row.get('productCode', '')
            if not product_name:
                continue
            item = {}
            item['spider_name']         = self.name
            item['_table']             = 'securities_private_equity_fund'
            item['product_name']        = product_name
            item['product_code']        = product_code
            item['administrator_name']  = row.get('mgrName')
            item['establish_date']      = _ts(row.get('foundDate'))
            item['filing_date']         = _ts(row.get('registeredDate'))
            item['fund_type']           = row.get('fundType')
            item['organizational_form'] = row.get('orgForm')
            item['operation_status']    = row.get('fundStatus')
            item['whether_trusteeship'] = row.get('tuoGuan')
            item['whether_name']        = row.get('trustee')
            item['fund_url']            = f"https://gs.amac.org.cn/amac-infodisc/res/pof/subfund/{row.get('id', '')}.html"
            item['md5_value']           = _md5(product_name, product_code)
            yield item

    # ------------------------------------------------------------------ #
    # 基金公司及子公司集合资管产品（subsidiary_aggregate_product）          #
    # ------------------------------------------------------------------ #
    def _parse_aggregate_list(self, response):
        try:
            rows = response.json().get('content') or []
        except Exception:
            return
        for row in rows:
            detail_url = f"https://gs.amac.org.cn/amac-infodisc/res/fund/account/{row.get('id', '')}.html"
            yield scrapy.Request(
                url=detail_url,
                headers=_HDRS_HTML,
                callback=self._parse_aggregate_detail,
                errback=self.errback,
                meta={'fund_url': detail_url},
            )

    def _parse_aggregate_detail(self, response):
        fund_url = response.meta['fund_url']
        try:
            tree = etree.HTML(response.body)
        except Exception:
            return
        tr_list = tree.xpath('//div[@class="info-body"]/div[1]/div[@class="table-response"]/table/tbody/tr')
        field_map = {
            '产品名称': 'product_name',
            '产品编码': 'product_code',
            '管理人名称': 'administrator_name',
            '托管人名称': 'custodian_name',
            '备案日期': 'filing_date',
            '成立日期': 'establish_date',
            '到期日': 'due_date',
            '投资类型': 'investment_type',
            '是否分级': 'whether_classification',
            '运作状态': 'operation_status',
        }
        result = {v: '' for v in field_map.values()}
        for tr in tr_list:
            title = _txt(tr.xpath('./td[1]/text()'))
            for k, v in field_map.items():
                if k in title:
                    result[v] = _txt(tr.xpath('./td[2]/text()'))
                    break

        product_name = result['product_name']
        if not product_name:
            return

        item = {}
        item['spider_name']            = self.name
        item['_table']             = 'subsidiary_aggregate_product'
        item['product_name']           = product_name
        item['product_code']           = result['product_code']
        item['administrator_name']     = result['administrator_name']
        item['custodian_name']         = result['custodian_name']
        item['filing_date']            = result['filing_date']
        item['establish_date']         = result['establish_date']
        item['due_date']               = result['due_date']
        item['investment_type']        = result['investment_type']
        item['whether_classification'] = result['whether_classification']
        item['operation_status']       = result['operation_status']
        item['fund_url']               = fund_url
        item['md5_value']              = _md5(product_name, result['product_code'])
        yield item

    # ------------------------------------------------------------------ #
    # 资产支持专项计划（asset_backed_plan）                                #
    # ------------------------------------------------------------------ #
    def _parse_abs(self, response):
        try:
            rows = response.json().get('content') or []
        except Exception:
            return
        for row in rows:
            product_code      = row.get('productCode', '')
            special_plan_name = row.get('productName', '')
            if not special_plan_name:
                continue
            item = {}
            item['spider_name']        = self.name
            item['_table']             = 'asset_backed_plan'
            item['product_code']       = product_code
            item['special_plan_name']  = special_plan_name
            item['administrator_name'] = row.get('orgName')
            item['whether_name']       = row.get('trustee')
            item['establish_date']     = _ts(row.get('fundFoundDate'))
            item['expire_date']        = _ts(row.get('fundDueDate'))
            item['adopt_date']         = _ts(row.get('registeredDate'))
            item['fund_url']           = response.url
            item['md5_value']          = _md5(special_plan_name, product_code)
            yield item

    # ------------------------------------------------------------------ #
    # 期货公司集合资管产品（futures_products）                             #
    # ------------------------------------------------------------------ #
    def _parse_futures(self, response):
        try:
            rows = response.json().get('content') or []
        except Exception:
            return
        for row in rows:
            product_name = row.get('mpiName', '')
            product_code = row.get('mpiProductCode', '')
            if not product_name:
                continue
            item = {}
            item['spider_name']            = self.name
            item['_table']             = 'futures_products'
            item['product_name']           = product_name
            item['product_code']           = product_code
            item['administrator_name']     = row.get('aoiName')
            item['custodian_name']         = row.get('mpiTrustee')
            item['filing_date']            = row.get('registeredDate')
            item['establish_date']         = row.get('mpiCreateDate')
            item['due_date']               = row.get('dueDate')
            item['investment_type']        = row.get('tzlx')
            item['whether_classification'] = row.get('sfjgh')
            item['operation_status']       = row.get('fundStatus')
            item['fund_url']               = f"https://gs.amac.org.cn/amac-infodisc/res/pof/futures/detail.html?id={row.get('id', '')}"
            item['md5_value']              = _md5(product_name, product_code)
            yield item

    # ------------------------------------------------------------------ #
    # 会员机构（member_mechanism）                                         #
    # ------------------------------------------------------------------ #
    def _parse_member_list(self, response):
        try:
            rows = response.json().get('content') or []
        except Exception:
            return
        for row in rows:
            uid = row.get('userTenantId', '')
            if not uid:
                continue
            url1 = f'https://gs.amac.org.cn/amac-infodisc/res/pof/member/{uid}.html'
            yield scrapy.Request(
                url=url1,
                headers=_HDRS_HTML,
                callback=self._parse_member_detail,
                errback=self.errback,
                meta={'uid': uid, 'url': url1},
            )

    def _parse_member_detail(self, response):
        meta = response.meta
        try:
            tree = etree.HTML(response.body)
        except Exception:
            return
        tr_list = tree.xpath('//div[@class="info-body"]/div[@class="section"][1]/div[@class="table-response"]/table/tbody/tr')
        field_map = {
            '全称(中文)': 'member_mechanism_name',
            '基金管理人全称(中文)': 'member_mechanism_name',
            '统一社会信用代码': 'Credit_code',
            '组织机构代码': 'Credit_code',
            '成立时间': 'establish_time',
            '注册地址': 'register_address',
            '办公地址': 'office_address',
            '注册资本(万元)': 'registered_capital',
            '机构性质': 'mechanism_nature',
            '企业性质': 'mechanism_nature',
            '机构类型': 'mechanism_type',
            '业务类型': 'business_type',
            '员工人数': 'staff_number',
            '机构网址': 'website',
            '当前会员类型': 'member_type',
            '入会时间': 'admission_time',
            '会员代表': 'member_representative',
            '会员编码': 'member_code',
        }
        result = {v: '' for v in field_map.values()}
        for tr in tr_list:
            title = _txt(tr.xpath('./td[1]/text()')) or _txt(tr.xpath('./td[1]/div/text()'))
            for k, v in field_map.items():
                if k in title:
                    result[v] = _txt(tr.xpath('./td[2]/text()')) or _txt(tr.xpath('./td/span/text()'))
                    break

        legal_representative = _txt(tree.xpath(
            '//div[@class="info-body"]/div[2]/div[@class="table-response"]/table/tbody/tr[1]/td[2]/text()'))
        senior_exec_trs = tree.xpath(
            '//div[@class="info-body"]/div[2]/div[@class="table-response"]/table/tbody/tr[2]/td[2]/table/tbody/tr')
        senior_executive = json.dumps([
            {
                'name': _txt(r.xpath('./td[1]/text()')),
                'post': _txt(r.xpath('./td[2]/text()')),
            } for r in senior_exec_trs
        ], ensure_ascii=False)

        name = result['member_mechanism_name']
        credit = result['Credit_code']
        if not name:
            return

        item = {}
        item['spider_name']           = self.name
        item['_table']             = 'member_mechanism'
        item['member_mechanism_name'] = name
        item['Credit_code']           = credit
        item['establish_time']        = result['establish_time']
        item['register_address']      = result['register_address']
        item['office_address']        = result['office_address']
        item['registered_capital']    = result['registered_capital']
        item['mechanism_nature']      = result['mechanism_nature']
        item['staff_number']          = result['staff_number']
        item['member_type']           = result['member_type']
        item['admission_time']        = result['admission_time']
        item['member_representative'] = result['member_representative']
        item['member_code']           = result['member_code']
        item['Legal_representative']  = legal_representative
        item['senior_executive']      = senior_executive
        item['mechanism_type']        = result['mechanism_type']
        item['business_type']         = result['business_type']
        item['website']               = result['website']
        item['url']                   = meta['url']
        item['md5_value']             = _md5(name, credit)
        yield item

    # ------------------------------------------------------------------ #
    # 私募基金管理人登记办理流程（private_fund_register_process）           #
    # ------------------------------------------------------------------ #
    def _parse_register_flow(self, response):
        try:
            rows = response.json().get('content') or []
        except Exception:
            return
        for row in rows:
            mechanism_name = row.get('orgName', '')
            if not mechanism_name:
                continue
            item = {}
            item['spider_name']                 = self.name
            item['_table']             = 'private_fund_register_process'
            item['mechanism_name']              = mechanism_name
            item['mechanism_type']              = row.get('orgTypeName')
            item['processing_status']           = row.get('orgStatusName')
            item['first_submission_date']       = _ts(row.get('firstSubmitDate'))
            item['feedback_date']               = _ts(row.get('firstReturnNoListDate'))
            item['feedback_number']             = row.get('noListReturnCount')
            item['start_processing_date']       = _ts(row.get('auditStartDate'))
            item['last_feedback_date']          = _ts(row.get('lastUpdateDate'))
            item['latest_submission_date']      = _ts(row.get('lastSubmitDate'))
            item['handling_feedback_number']    = row.get('lastFixedCount')
            item['accumulated_processing_time'] = row.get('totalAuditDay')
            item['accumulated_material_time']   = row.get('newTotalFixedDay')
            item['registered_address']          = row.get('registerAddress')
            item['office_location']             = row.get('officeAddress')
            item['law_firm']                    = row.get('latfirmName')
            item['lead_lawyer']                 = row.get('legallerName')
            item['md5_value']                   = _md5(mechanism_name)
            yield item

    # ------------------------------------------------------------------ #
    # 已注销私募基金管理人（cancel_the_fund_manager）                       #
    # ------------------------------------------------------------------ #
    def _parse_cancelled_list(self, response):
        try:
            rows = response.json().get('content') or []
        except Exception:
            return
        for row in rows:
            uid = row.get('userTenantId', '')
            if not uid:
                continue
            detail_url = f'https://gs.amac.org.cn/amac-infodisc/res/cancelled/manager/{uid}.html'
            yield scrapy.Request(
                url=detail_url,
                headers=_HDRS_HTML,
                callback=self._parse_cancelled_detail,
                errback=self.errback,
                meta={'fund_url': detail_url},
            )

    def _parse_cancelled_detail(self, response):
        fund_url = response.meta['fund_url']
        try:
            tree = etree.HTML(response.body)
        except Exception:
            return

        cancel_trs = tree.xpath('//div[@class="info-body"]/div/div[1]/div[1]/table/tbody/tr')
        cancellation_date = _txt(cancel_trs[0].xpath('./td[2]/text()')) if cancel_trs else ''
        cancellation_type = _txt(cancel_trs[1].xpath('./td[2]/text()')) if len(cancel_trs) > 1 else ''

        info_trs = tree.xpath('//div[@class="info-body"]/div/div[1]/div[3]/table/tbody/tr')
        field_map = {
            '基金管理人全称(中文)': 'manager_name',
            '统一社会信用代码': 'unified_credit_code',
            '注册地址': 'registration_location',
            '办公地址': 'office_location',
            '注册资本(万元)人民币': 'registered_capital',
            '实缴资本(万元)人民币': 'Paid_in',
            '企业性质': 'Enterprise_nature',
            '机构类型': 'organization_type',
            '机构网址': 'mechanism_website',
        }
        result = {v: '' for v in field_map.values()}
        for tr in info_trs:
            title = _txt(tr.xpath('./td[1]/text()'))
            for k, v in field_map.items():
                if k in title:
                    result[v] = _txt(tr.xpath('./td[2]/text()')) or _txt(tr.xpath('./td[2]/span/text()'))
                    break

        actual_controller = _txt(tree.xpath(
            '//div[@class="info-body"]/div/div[2]/div[2]/table/tbody/tr/td[2]/text()'))

        exec_trs = tree.xpath('//div[@class="info-body"]/div/div[3]/div[2]/table/tbody/tr/td[2]/table/tbody/tr')
        exec_info = [{'serial_number': _txt(r.xpath('./td[1]/text()')), 'post': _txt(r.xpath('./td[2]/text()')), 'name': _txt(r.xpath('./td[3]/text()'))} for r in exec_trs]

        related_trs = tree.xpath('//div[@class="info-body"]/div/div[4]/div[2]/table/tbody/tr/td[2]/table/tbody/tr')
        related_info = [{'serial_number': _txt(r.xpath('./td[1]/text()')), 'type': _txt(r.xpath('./td[2]/text()')), 'name': _txt(r.xpath('./td[3]/text()'))} for r in related_trs]

        investor_trs = tree.xpath('//div[@class="info-body"]/div/div[5]/div[2]/table/tbody/tr/td[2]/table/tbody/tr')
        investor_info = [{'serial_number': _txt(r.xpath('./td[1]/text()')), 'name': _txt(r.xpath('./td[2]/text()'))} for r in investor_trs]

        product_info = {'cleared_products': [], 'unclear_products': []}

        manager_name = result['manager_name']
        unified_credit_code = result['unified_credit_code']
        if not manager_name:
            return

        item = {}
        item['spider_name']               = self.name
        item['_table']             = 'cancel_the_fund_manager'
        item['cancellation_date']         = cancellation_date
        item['cancellation_type']         = cancellation_type
        item['manager_name']              = manager_name
        item['unified_credit_code']       = unified_credit_code
        item['registration_location']     = result['registration_location']
        item['office_location']           = result['office_location']
        item['registered_capital']        = result['registered_capital']
        item['Paid_in']                   = result['Paid_in']
        item['Enterprise_nature']         = result['Enterprise_nature']
        item['organization_type']         = result['organization_type']
        item['mechanism_website']         = result['mechanism_website']
        item['actual_controller']         = actual_controller
        item['Executive_Information']     = json.dumps(exec_info, ensure_ascii=False)
        item['Related_party_information'] = json.dumps(related_info, ensure_ascii=False)
        item['Investor_Information']      = json.dumps(investor_info, ensure_ascii=False)
        item['Product_Information']       = json.dumps(product_info, ensure_ascii=False)
        item['fund_url']                  = fund_url
        item['md5_value']                 = _md5(manager_name, unified_credit_code)
        yield item

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
