import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from spiders.law.law_case.law_alk_12348 import case_area_list
from utils.tools import *
from utils.time_kit import *

class AlkPremiumCaseSpider(BaseSpider):
    name = 'alk_premium_case'
    data_table = 'case_parse_judicial'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://alk.12348.gov.cn",
        "Pragma": "no-cache",
        "Referer": "https://alk.12348.gov.cn/LawSelect/SearchIndex?checkDatabaseID=48%2C49",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": "\"Chromium\";v=\"146\", \"Not-A.Brand\";v=\"24\", \"Google Chrome\";v=\"146\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            base_url = "https://alk.12348.gov.cn/LawSelect/Search"
            data = {
                "searchField": "案例全文",
                "keywords": "",
                "checkDatabaseID": "0,48,49,0,46,47,0,44,66,0,56,57,58,0,28,29,30,31,68,69,70,67,83,36,79,81,82,0,40,41,42,43,0,23,24,25,26,27,0,18,20,21,22,0,59,60,63,64,0,37,38,39,0,50,52,0,74,75,76,77,",
                "pageIndexNow": str(page),
                "pageSizeNow": "10",
                "sortField": "",
                "sortDescAsc": "",
                "listOrabst": "",
                "classCode": "",
                "fieldName": "",
                "fieldValue": "",
                "currentSubid": "0",
                "caseTimeValue": "",
                "businessTypeName": "",
                "areaName": "",
                "Type": "0",
                "ParentDbId": ""
            }
            yield scrapy.FormRequest(
                url=base_url,
                method="POST",
                headers=self.headers,
                formdata=data,
                callback=self.parse_list,
                dont_filter=True,
                cb_kwargs={'bond_type': '精品案例'}
        )

    def parse_list(self, response, bond_type):
        soup = BeautifulSoup(response.text, "lxml")
        for data in soup.select('[class="sortlist"]>table>tbody>tr'):
            case_url = "https://alk.12348.gov.cn" + data.select('td')[0].a['href']
            case_title = data.select('td')[0].a['title']
            case_number = data.select('td')[1].text
            case_submission_time = data.select('td')[2].text
            case_type = data.select('td')[3].text
            url_list = {'case_url':case_url, 'case_title': case_title, "case_number":case_number, "case_submission_time":case_submission_time, 'case_type':case_type, 'bond_type': bond_type}
            yield scrapy.Request(
                url=url_list['case_url'],
                method="GET",
                headers=self.headers,
                callback=self.parse_content,
                cb_kwargs={'list_data': url_list}
            )


    def text_classification(self, soup):
        case_introduction = ''  #案情简介
        case_study = ''     #案例思考
        case_review = ''    #案件点评
        reason_for_recommendation = ''  #推荐理由
        expert_analysis = ''    #专家评析
        key_issue_in_dispute = ''   #争议焦点
        adjudication_result = ''    #裁决结果
        relevant_laws = ''  #相关法律
        conclusion_suggestions = '' #结语和建议
        mediation_process = '' # 调解过程
        notarial_certificate = '' # 公证书格式
        content_title = soup.select('[class="wzinfo"]>h6')
        content_con = soup.select('[class="wzinfo"]>.contentspan')
        for list in range(len(content_title)):
            if '背景' in content_title[list].text or '情况' in content_title[list].text or '基本' in content_title[list].text or '简介' in content_title[list].text or '概况' in content_title[list].text or '概要' in content_title[list].text:
                case_introduction += f"{content_con[list]}"
            if '思考' in content_title[list].text:
                case_study += f"{content_con[list]}"
            if '点评' in content_title[list].text:
                case_review += f"{content_con[list]}"
            if '理由' in content_title[list].text:
                reason_for_recommendation += f"{content_con[list]}"
            if '评析' in content_title[list].text:
                expert_analysis += f"{content_con[list]}"
            if '结果' in content_title[list].text or '裁判文书' in content_title[list].text or '效果' in content_title[list].text or '措施' in content_title[list].text or '成效' in content_title[list].text:
                adjudication_result += f"{content_con[list]}"
            if '焦点' in content_title[list].text:
                key_issue_in_dispute += f"{content_con[list]}"
            if '法律' in content_title[list].text:
                relevant_laws += f"{content_con[list]}"
            if '建议' in content_title[list].text or '意见' in content_title[list].text:
                conclusion_suggestions += f"{content_con[list]}"
            if '过程' in content_title[list].text:
                mediation_process += f"{content_con[list]}"
            if '公证书' in content_title[list].text:
                notarial_certificate += f"{content_con[list]}"

        return {"case_introduction": case_introduction, "case_study": case_study, "case_review": case_review, 'reason_for_recommendation': reason_for_recommendation, 'expert_analysis': expert_analysis,
                'key_issue_in_dispute': key_issue_in_dispute, 'adjudication_result': adjudication_result, 'relevant_laws': relevant_laws, 'conclusion_suggestions': conclusion_suggestions,
                'mediation_process': mediation_process, 'notarial_certificate': notarial_certificate}

    def get_area(self, case_url, case_number):
        area_number = case_number.split((re.findall(r'dbName=(.*?)&', case_url)[0]))[0]
        if area_number == '':
            return '新疆兵团'
        else:
            return case_area_list.case_area_data[area_number]

    def parse_content(self, response, list_data):
        soup = BeautifulSoup(response.text, "lxml")
        data = soup.select('[class="wzinfo"]')
        if data:
            content_data = self.text_classification(soup)

            item_mains = {}
            # item_main.spider_name = self.spider_name
            item_mains['md5_value'] = hash_md5(list_data['case_url'] + list_data['case_title'] + list_data['case_number'])
            item_mains['web_name'] = "中国法律服务网-司法行政（法律服务）案例库"
            item_mains['web_url'] = "https://alk.12348.gov.cn/"
            item_mains['source'] = list_data['case_url']
            item_mains['title'] = list_data['case_title']
            item_mains['case_type'] = list_data['case_type']
            item_mains['case_submission_time'] = list_data['case_submission_time']
            item_mains['case_number'] = list_data['case_number']
            item_mains['case_area'] = self.get_area(list_data['case_url'], list_data['case_number'])
            item_mains['bond_type'] = list_data['bond_type']
            item_mains['case_introduction'] = content_data['case_introduction']
            item_mains['case_study'] = content_data['case_study']
            item_mains['case_review'] = content_data['case_review']
            item_mains['reason_for_recommendation'] = content_data['reason_for_recommendation']
            item_mains['expert_analysis'] = content_data['expert_analysis']
            item_mains['key_issue_in_dispute'] = content_data['key_issue_in_dispute']
            item_mains['adjudication_result'] = content_data['adjudication_result']
            item_mains['relevant_laws'] = content_data['relevant_laws']
            item_mains['conclusion_suggestions'] = content_data['conclusion_suggestions']
            item_mains['mediation_process'] = content_data['mediation_process']
            item_mains['notarial_certificate'] = content_data['notarial_certificate']
            if content_data['adjudication_result'] != "":
                # insert_data(table='case_parse_judicial', data=item_main)
                yield item_mains
            else:
                logger.warning(f'{self.name} crawling source:{list_data["case_url"]}  不包含结果，被去除')


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')