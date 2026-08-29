import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *


class IpoDeclareBseSpider(BaseSpider):
    name = 'ipo_declare_bse'
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
        "Accept": "text/javascript, application/javascript, application/ecmascript, application/x-ecmascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://www.bse.cn",
        "Referer": "https://www.bse.cn/audit/project_news.html",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    base_url = 'https://www.bse.cn/projectNewsController/infoResult.do'
    detail_url = 'https://www.bse.cn/projectNewsController/infoDetailResult.do'
    examine_status = {'p01': '已受理', 'p02': '已问询', 'p03': '上市委会议通过', 'p04': '上市委会议未通过',
                               'p05': '上市委会议暂缓', 'po6': '提交注册', 'p07-1': '注册', 'p07-2': '核准',
                               'p08': '核准', 'p09': '中止', 'p10': '终止'}

    @staticmethod
    def generate_data(page, state_type):
        data = {
            'statetypes[]': state_type,
            'page': str(page),
            'companyCode': '',
            'isNewThree': '1',
            'sortfield': 'updateDate',
            'sorttype': 'desc',
            'keyword': '',
            'needFields[]': [
                'id',
                'stockCode',
                'stockName',
                'companyName',
                'status',
                'registerAddress',
                'sponsorOrg',
                'appraisalOrg',
                'lawyerOrg',
                'accountingOrg',
                'updateDate',
                'receiveDate',
                'operatingTime',
            ],
        }
        return data

    def start_requests(self):
        for state_type, examine_status in self.examine_status.items():
            for page in range(self.start_page -1, self.end_page):
                data = self.generate_data(page, state_type)
                yield scrapy.FormRequest(
                    url=self.base_url,
                    method='POST',
                    headers=self.headers,
                    formdata=data,
                    callback=self.parse_list,
                    dont_filter=True,
                    cb_kwargs={'examine': examine_status},
                    errback=self.errback
                )
                # response = common_request(self.base_url, headers=self.headers, data=data, method='post')
                # yield from self.parse_list(response, examine_status)

    def parse_list(self, response, examine):
        result = re.findall(r'null\(\[(.*)]\)', response.text)
        res = json.loads(result[0])
        datas = res['listInfo']['content']
        for data in datas:
            detail_id = data['id']
            examine_status = data['status']
            temp = {'detail_id': detail_id, 'examine_status': examine_status}
            form_data = {
                'id': str(temp['detail_id']),
            }
            yield scrapy.FormRequest(
                url=self.detail_url,
                method='POST',
                headers=self.headers,
                formdata=form_data,
                callback=self.parse_detail,
                dont_filter=True,
                cb_kwargs={'examine': examine}
            )

    def parse_detail(self, response, examine):
        self.log_info(f"examine: {examine}")
        result = re.findall(r'null\(\[(.*)]\)', response.text)
        res = json.loads(result[0])
        ipo_status = self.handle_project_status(res['projectStatus'])

        project_news = res['projectNews']
        entity_name = project_news['companyName']
        acceptance_date = str(timestamp_to_datetime(project_news['receiveDate']['time']))
        update_date = str(timestamp_to_datetime(project_news['publishDate']['time']))
        industry_sponsorship = project_news['sponsorOrg']
        representative_person = project_news['sponsorRepresent']
        accounting_firm = project_news['accountingOrg']
        accountant = project_news['accountant']
        law_firm = project_news['lawyerOrg']
        lawyer = project_news['lawyer']
        evaluation_agency = project_news.get('appraisalOrg')
        evaluator = project_news.get('appraiser')
        registered_address = project_news['registerAddress']

        md5_value = hash_md5(entity_name + str(update_date) + examine)
        items = {}
        items['entity_name'] = entity_name
        items['acceptance_date'] = acceptance_date
        items['update_date'] = update_date
        items['financing_amount'] = None
        items['examine_status'] = examine
        items['proposed_listing_location'] = '北交所'
        items['industry'] = None
        items['industry_sponsorship'] = industry_sponsorship
        items['representative_person'] = representative_person
        items['accounting_firm'] = accounting_firm
        items['accountant'] = accountant
        items['law_firm'] = law_firm
        items['lawyer'] = lawyer
        items['evaluation_agency'] = evaluation_agency
        items['evaluator'] = evaluator
        items['registered_address'] = registered_address
        items['source'] = '北交所'
        items['ipo_status'] = ipo_status
        items['md5_value'] = md5_value
        # insert_data(table='entity_ipo_declare_a_shares', data=item)
        items['_table'] = 'entity_ipo_declare_a_shares'
        yield items
        yield from self.parse_ipo_file(response, md5_value)

    @staticmethod
    def handle_project_status(res):
        register_result = {'1': '注册', '2': '核准'}
        ipo_status = []
        receive = res.get('receiveDate')
        inquiry = res.get('inquiryDate')
        listing = res.get('listingCommitteeResultDate')
        submit = res.get('submitDate')
        approve = res.get('approveResultDate')
        for examine_status, timestamp in {'已受理': receive, '已问询': inquiry, '上市委会议': listing,
                                          '提交注册': submit, '注册结果': approve}.items():
            if timestamp:
                publish_date = timestamp_to_datetime(timestamp['time'])
                if examine_status == '注册结果':
                    examine_status = register_result.get(res['approveResult'])
                temp = {'publish_date': str(publish_date), 'examine_status': examine_status}
                ipo_status.append(temp)
        return str(ipo_status)

    def parse_ipo_file(self, response, ipo_md5_value):
        result = re.findall(r'null\(\[(.*)]\)', response.text)
        res = json.loads(result[0])
        # 信息披露
        info_result = res['xxgkInfo']
        self.parse_info_result(info_result, ipo_md5_value)

        ask_response_result = res['wxhfhInfo']
        meeting_result = res['hyggjgInfo']
        register_result = res['hztzInfo']
        for file_type, result in {'上市委会议公告和结果': meeting_result,
                                  '问询与回复': ask_response_result,
                                  '注册结果': register_result}.items():
            yield from self.parse_file_data(result, file_type, ipo_md5_value, file_version=None)

    def parse_info_result(self, info_result, ipo_md5_value):
        # 解析信息披露
        temp_file_type = {'FYYJS': '法律意见书', 'GPFXBJS': '发行保荐书', 'GPFXSMS': '招股说明书',
                          'GPZJXCGPTJS': '上市保荐书', 'SJBG': '财务报告和审计报告'}
        temp_file_versiom = {'BHG': '注册稿', 'SBG': '申报稿', 'SYG': '上会稿'}
        for temp_type, result in info_result.items():
            if 'QT' in temp_type:
                continue
            file_type = temp_file_type[temp_type]
            for temp_version, res in result.items():
                file_version = temp_file_versiom[temp_version]
                yield from self.parse_file_data(res, file_type, ipo_md5_value, file_version)

    def parse_file_data(self, result, file_type, ipo_md5_value, file_version):
        # logger.warning(f'{self.spider_name} parse file filetype: {file_type}')
        for res in result:
            publish_date = res['publishDate']
            attachment_title = res['disclosureTitle']
            href = res['destFilePath']
            attachment_url = urljoin('https://www.bse.cn', href)

            items = {}
            items['ipo_md5_value'] = ipo_md5_value
            items['file_type'] = file_type
            items['file_version'] = file_version
            items['publish_date'] = str(publish_date)
            items['attachment_title'] = attachment_title
            items['attachment_url'] = attachment_url
            items['md5_value'] = hash_md5(ipo_md5_value + attachment_title + str(publish_date))
            # insert_data('entity_ipo_declare_a_shares_mapping', data=item)
            items['_table'] = 'entity_ipo_declare_a_shares_mapping'
            yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
