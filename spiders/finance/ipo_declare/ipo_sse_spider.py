import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class IpoDeclareSseSpider(BaseSpider):
    name = 'ipo_declare_sse'
    # data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://listing.sse.com.cn/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',

    }
    base_url = 'https://query.sse.com.cn/commonSoaQuery.do'
    board = {'1': '科创板', '2': '沪主板'}
    examine_status = {'1': '已受理', '2': '已问询', '3': '上市委审议', '4': '提交注册', '5': '注册结果',
                           '7': '中止(财报更新)', '8': '终止', '9': '上市委审议', '10': '补充审核'}
    commit_status = {'6': '暂缓审议', '1': '上市委会议通过', '3': '上市委会议未通过', '4': '复审委会议通过',
                          '5': '复审委会议未通过'}
    register_status = {'1': '注册生效', '2': '不予注册', '3': '终止注册'}

    @staticmethod
    def generate_params(page):
        params = {
            'jsonCallBack': '',
            'isPagination': 'true',
            'sqlId': 'SH_XM_LB',
            'pageHelp.pageSize': '20',
            'offerType': '',
            'commitiResult': '',
            'registeResult': '',
            'issueMarketType': '1,2',
            'province': '',
            'currStatus': '',
            'order': 'updateDate|desc,stockAuditNum|desc',
            'keyword': '',
            'auditApplyDateBegin': '',
            'auditApplyDateEnd': '',
            'pageHelp.pageNo': page,
            'pageHelp.beginPage': page,
            'pageHelp.endPage': page,
        }
        return params

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            params = self.generate_params(page)
            url = f"{self.base_url}?{urlencode(params, doseq=True)}"

            yield scrapy.Request(
                url=url,
                headers=self.headers,
                callback=self.parse_list,
            )

    def parse_list(self, response):
        result = response.json()['result']
        for data in result:
            audit_num = data['stockAuditNum']
            # ipo_process = self.get_ipo_process(audit_num)
            req_params = {'isPagination': 'false', 'sqlId': 'GP_GPZCZ_XMDTZTTLB', 'stockAuditNum': audit_num}
            req_url = f"{self.base_url}?{urlencode(req_params, doseq=True)}"
            yield scrapy.Request(
                url=req_url,
                method="GET",
                headers=self.headers,
                callback=self.get_ipo_process,
                cb_kwargs={'data': data, 'audit_num': audit_num},
            )

    def get_ipo_process(self, response, data, audit_num):
        # 获取ipo进程状态
        ipo_process = []
        if response:
            try:
                result = response.json()['result']
                for data_data in result:
                    publish_date = data_data['publishDate']
                    current_status = data_data['auditStatus']
                    commit_result = data_data['commitiResult']
                    register_result = data_data['registeResult']
                    examine_status = self.handle_examine_status(current_status, commit_result, register_result)
                    temp = {'publish_date': publish_date, 'examine_status': examine_status}
                    ipo_process.append(temp)
            except Exception as e:
                msg = f'{self.base_url} ipo进程解析错误：{e}'
                self.log_error(msg)
                # send_dd_msg(self.spider_name, '解析失败', msg)

        ipo_process = str(ipo_process)
        entity_name = data['stockAuditName']
        acceptance_date = format_datetime(data['auditApplyDate'], format_str='%Y%m%d%H%M%S').date()
        update_date = format_datetime(data['updateDate'], format_str='%Y%m%d%H%M%S').date()
        financing_amount = data['planIssueCapital']

        current_status = data['currStatus']
        commit_result = data['commitiResult']
        register_result = data['registeResult']
        examine_status = self.handle_examine_status(current_status, commit_result, register_result)

        proposed_listing_location = self.board.get(str(data['issueMarketType']))
        issuer = data['stockIssuer'][-1]
        industry = issuer['s_csrcCodeDesc']
        province = issuer['s_province']
        city = issuer['s_areaNameDesc']
        temp = self.handle_person(data)

        md5_value = hash_md5(entity_name+str(update_date)+examine_status)
        items = {}
        items['entity_name'] = entity_name
        items['acceptance_date'] = acceptance_date
        items['update_date'] = str(update_date)
        items['financing_amount'] = financing_amount
        items['examine_status'] = examine_status
        items['proposed_listing_location'] = proposed_listing_location
        items['industry'] = industry
        items['industry_sponsorship'] = temp.get('industry_sponsorship')
        items['representative_person'] = temp.get('representative_person')
        items['accounting_firm'] = temp.get('accounting_firm')
        items['accountant'] = temp.get('accountant')
        items['law_firm'] = temp.get('law_firm')
        items['lawyer'] = temp.get('lawyer')
        items['evaluation_agency'] = temp.get('evaluation_agency')
        items['evaluator'] = temp.get('evaluator')
        items['registered_address'] = province
        items['ipo_status'] = ipo_process
        items['source'] = '上交所'
        items['md5_value'] = md5_value
        # insert_data(table='entity_ipo_declare_a_shares', data=item)
        items['_table'] = 'entity_ipo_declare_a_shares'
        yield items
        # self.attach_list.append({'audit_num': audit_num, 'md5_value': md5_value})
        # 附件部分
        temps = {'audit_num': audit_num, 'md5_value': md5_value}
        req_params = self.generate_ipo_ann_params(temps['audit_num'])
        req_url = f"{self.base_url}?{urlencode(req_params, doseq=True)}"
        yield scrapy.Request(
            url=req_url,
            method="GET",
            headers=self.headers,
            callback=self.parse_ipo_announcement,
            cb_kwargs={'data': temps},
        )

    def parse_ipo_announcement(self, response, data):
        # 解析申报相关的文件
        ipo_md5_value = data['md5_value']
        temp_version = {1: '申报稿', 2: '上会稿', 3: '注册稿'}
        temp_type = {
            1: '上市委会议公告和结果',
            2: '上市委会议公告和结果',
            30: '招股说明书',
            32: '审计报告',
            33: '法律意见书',
            35: '注册结果',
            36: '发行保荐书',
            37: '上市保荐书',
            '': '问询与回复',
        }

        result = response.json()['result']
        for res in result:
            attachment_title = res['fileTitle']
            href = res['filePath']
            attachment_url = 'https://static.sse.com.cn/stock' + href
            publish_date = format_datetime(res['fileUpdTime'], format_str='%Y%m%d%H%M%S').date()
            file_version = temp_version.get(res['fileVersion'])
            file_type = temp_type.get(res['fileType'])

            items = {}
            items['ipo_md5_value'] = ipo_md5_value
            items['file_type'] = file_type
            items['file_version'] = file_version
            items['publish_date'] = str(publish_date)
            items['attachment_title'] = attachment_title
            items['attachment_url'] = attachment_url
            items['md5_value'] = hash_md5(ipo_md5_value+attachment_title+str(publish_date))
            # insert_data('entity_ipo_declare_a_shares_mapping', data=item)
            items['_table'] = 'entity_ipo_declare_a_shares_mapping'
            yield items

    @staticmethod
    def generate_ipo_ann_params(audit_num):
        params = {
            'jsonCallBack': '',
            'isPagination': 'false',
            'sqlId': 'GP_COMMON_FILE_SEARCH',
            'auditId': audit_num,
            'marketType': '1,2',
        }
        return params

    def handle_examine_status(self, current_status, commit_result, register_result):
        examine_status = self.examine_status.get(str(current_status))
        if commit_result:
            examine_status = self.commit_status.get(str(commit_result))
        if register_result:
            examine_status = self.register_status.get(str(register_result))
        return examine_status

    @staticmethod
    def handle_person(data):
        intermediaries = data['intermediary']

        temp = {}
        for intermediary in intermediaries:
            name = intermediary['i_intermediaryName']
            person = intermediary['i_person']

            person_list = [p['i_p_personName'] for p in person if '保荐代表人' in p['i_p_jobTitle'] or
                           '签字会计师' in p['i_p_jobTitle'] or '签字律师' in p['i_p_jobTitle']
                           or '签字评估师' in p['i_p_jobTitle']]
            person_str = ','.join(person_list)
            if '证券' in name:
                temp.update({'industry_sponsorship': name, 'representative_person': person_str})
            elif '会计' in name:
                temp.update({'accounting_firm': name, 'accountant': person_str})
            elif '律师' in name:
                temp.update({'law_firm': name, 'lawyer': person_str})
            elif '评估' in name:
                temp.update({'evaluation_agency': name, 'evaluator': person_str})
        return temp


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')