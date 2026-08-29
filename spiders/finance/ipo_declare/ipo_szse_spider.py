import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class IpoDeclareSzseSpider(BaseSpider):
    name = 'ipo_declare_szse'
    data_table = ''
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://listing.szse.cn/projectdynamic/ipo/index.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    }

    base_url = 'https://listing.szse.cn/api/ras/projectrends/query'
    detail_url = 'https://listing.szse.cn/api/ras/projectrends/details'
    temp_version = {1: '申报稿', 2: '上会稿', 3: '注册稿'}

    @staticmethod
    def generate_params(page):
        params = {
            'bizType': '1',
            'pageIndex': page,
            'pageSize': '10',
        }
        return params

    def start_requests(self):
        for page in range(self.start_page - 1, self.end_page):
            params = self.generate_params(page)
            url = f"{self.base_url}?{urlencode(params, doseq=True)}"
            yield scrapy.Request(
                url=url,
                headers=self.headers,
                callback=self.get_list,
            )

    def get_list(self, response):
        result = response.json()['data']
        for data in result:
            com_id = data['prjid']
            params = {'id': com_id}
            url = f"{self.detail_url}?{urlencode(params, doseq=True)}"
            yield scrapy.Request(
                url=url,
                headers=self.headers,
                callback=self.parse_detail,
            )

    def parse_detail(self, response):
        result = response.json()['data']
        entity_name = result['cmpnm']
        acceptance_date = result['acptdt']
        update_date = result['updtdt']
        financing_amount = result['maramt']
        examine_status = result['prjst']
        proposed_listing_location = result['boardName']
        proposed_listing_location = '深主板' if '主板' in proposed_listing_location else proposed_listing_location
        industry = result['csrcind']
        industry_sponsorship = result['sprinst']
        representative_person = result['sprrep']
        accounting_firm = result['acctfm']
        accountant = result['acctsgnt']
        law_firm = result['lawfm']
        lawyer = result['lglsgnt']
        evaluation_agency = result['evalinst']
        evaluator = result['evalsgnt']
        province = result['regloc']

        ipo_status = self.handle_ipo_process(result)

        md5_value = hash_md5(entity_name + str(update_date) + examine_status)
        items = {}
        items['entity_name'] = entity_name
        items['acceptance_date'] = acceptance_date
        items['update_date'] = update_date
        items['financing_amount'] = financing_amount
        items['examine_status'] = examine_status
        items['proposed_listing_location'] = proposed_listing_location
        items['industry'] = industry
        items['industry_sponsorship'] = industry_sponsorship
        items['representative_person'] = representative_person
        items['accounting_firm'] = accounting_firm
        items['accountant'] = accountant
        items['law_firm'] = law_firm
        items['lawyer'] = lawyer
        items['evaluation_agency'] = evaluation_agency
        items['evaluator'] = evaluator
        items['registered_address'] = province
        items['source'] = '深交所'
        items['ipo_status'] = ipo_status
        items['md5_value'] = md5_value
        # insert_data(table='entity_ipo_declare_a_shares', data=item)
        items['_table'] = 'entity_ipo_declare_a_shares'
        yield items
        # return md5_value
        yield from self.parse_ipo_file(response, md5_value)

    def parse_ipo_file(self, response, ipo_md5_value):
        result = response.json()['data']
        info_result = result['disclosureMaterials']
        meeting_result = result['meetingConclusionAttachment']
        ask_response_result = result['enquiryResponseAttachment']
        register_result = result['registrationResultAttachment']
        for file_type, result in {'': info_result,
                                  '上市委会议公告和结果': meeting_result,
                                  '问询与回复': ask_response_result,
                                  '注册结果': register_result}.items():
            yield from self.insert_file_data(result, file_type, ipo_md5_value)

    def insert_file_data(self, result, file_type, ipo_md5_value):
        # logger.warning(f'{self.spider_name} parse file filetype: {file_type}')
        for res in result:
            file_type = file_type if file_type == '' else res['matnm']
            file_version = self.temp_version.get(res['dtyp'])
            publish_date = res['ddt']
            attachment_title = res['dfnm']
            href = res['dfpth']
            attachment_url = urljoin('https://reportdocs.static.szse.cn/', href)

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

    @staticmethod
    def handle_ipo_process(result):
        ipo_process = []
        datas = result['prjprogs']
        for data in datas:
            publish_date = data['date']
            examine_status = data['caption']
            temp = {'publish_date': publish_date, 'examine_status': examine_status}
            ipo_process.append(temp)
        return str(ipo_process)

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')