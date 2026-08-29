"""AMAC 私募基金产品 → private_fund_products"""
import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *

_LIST_URL = 'https://gs.amac.org.cn/amac-infodisc/api/pof/fund?&page={p}&size=20'


class AmacProductsSpider(BaseSpider):
    name = 'amac_products'
    data_table = 'private_fund_products'
    allowed_domains = ['gs.amac.org.cn']
    default_end_page = 2
    custom_settings = {
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'
    dedup_fields = ['md5_value']
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Origin": "https://gs.amac.org.cn",
        # "Referer": "https://gs.amac.org.cn/amac-infodisc/res/cancelled/manager/index.html",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    def replace_data(self, data):
        if data:
            return (data[0].strip().replace('\n', '').replace(u'\xa0', '').
                    replace("'", '`').replace('"', '”'))
        else:
            return ''

    def parse_item(self, details_tr_list):
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
            '基金备案阶段': 'fund_registration_stage',
            '币种': 'currency',
        }
        result = {var: '' for var in field_map.values()}
        # 获取标题
        for tr_data in details_tr_list:
            td_title = self.replace_data(tr_data.xpath('./td[1]/text()'))
            # 遍历字典，匹配标题并设置对应变量
            for title, var_name in field_map.items():
                if title in td_title:
                    text1 = self.replace_data(tr_data.xpath('./td[2]/text()'))
                    text2 = self.replace_data(tr_data.xpath('./td[2]/a/text()'))
                    result[var_name] = text1 if text1 else text2
                    break
        return result

    def start_requests(self):
        url = f'https://gs.amac.org.cn/amac-infodisc/api/pof/fund?&page=0&size=20'
        yield scrapy.Request(
            url=url,
            method="POST",
            headers=self.headers,
            body=json.dumps({}, separators=(",", ":")),
            callback=self.parse_total_pages,
            dont_filter=True,
        )

    def parse_total_pages(self, response):
        if int(self.end_page) < 0:
            count_page = response.json()['totalPages']
            pages = [page for page in range(int(self.start_page) - 1, int(count_page))]
        else:
            pages = [page for page in range(int(self.start_page) - 1, int(self.end_page))]
        for page in pages:
            url = f'https://gs.amac.org.cn/amac-infodisc/api/pof/fund?&page={page}&size=20'
            yield scrapy.Request(
                url=url,
                method="POST",
                headers=self.headers,
                body=json.dumps({}, separators=(",", ":")),
                callback=self.parse_list,
                dont_filter=True,
            )

    def parse_list(self, response):
        response = response.json()
        for content_data in reversed(response['content']):
            details_url = 'https://gs.amac.org.cn/amac-infodisc/res/pof/fund/' + content_data['url']
            yield scrapy.Request(
                url=details_url,
                headers=self.headers,
                method="GET",
                errback=self.errback,
                callback=self.parse_urls,
                cb_kwargs={'details_url': details_url}
            )

    def parse_urls(self, response, details_url):
        details_lement = etree.HTML(response.body)
        details_tr_list = details_lement.xpath(
            '//div[@class="info-body"]/div[1]/div[@class="table-response"]/table/tbody/tr')
        result = self.parse_item(details_tr_list)
        information_disclosure = self.get_information_disclosure(response)
        if result:
            fund_name = result['fund_name']
            manager_name = result['manager_name']
            legal_person = result['legal_person']
            founded_date = result['founded_date']
            registration_date = result['registration_date']
            proficient_type = result['proficient_type']
            fund_number = result['fund_number']
            fund_state = result['fund_state']
            last_updatetime = result['last_updatetime']
            administration_type = result['administration_type']
            # 新增字段
            fund_registration_stage = result['fund_registration_stage']
            currency = result['currency']
            information_disclosure = information_disclosure


            # 构建入库字段
            md5_value = hash_md5(manager_name)
            items = {}
            items['md5_value'] = md5_value
            items['fund_name'] = fund_name
            items['manager_name'] = manager_name
            items['legal_person'] = legal_person
            items['founded_date'] = founded_date
            items['registration_date'] = registration_date
            items['proficient_type'] = proficient_type
            items['fund_number'] = fund_number
            items['fund_state'] = fund_state
            items['fund_url'] = details_url
            items['last_updatetime'] = last_updatetime
            items['administration_type'] = administration_type
            # 新增字段
            items['fund_registration_stage'] = fund_registration_stage
            items['currency'] = currency
            items['information_disclosure'] = information_disclosure
            # insert_data(table='private_fund_products', data=item)
            yield items
        else:
            self.log_error(f'私募基金产品数据为空，url：{details_url}')

    def replace_data_rn(self, data):
        if data:
            return (data.strip().replace('\n', '').replace('\r', '').replace(' ', '').strip().replace(u'\xa0', '').
                    replace("'", '`').replace('"', '”'))
        else:
            return ''


    def get_information_disclosure(self, response):
        information_disclosure = []
        soup = BeautifulSoup(response.body, 'lxml')
        for data_list in soup.select('.info-body>.section')[-1].select('.table-response>table>tbody>tr'):
            key_name = self.replace_data_rn(data_list.select('td')[0].text.strip())
            key_value = self.replace_data_rn(data_list.select('td')[1].text.strip())
            information_disclosure.append({"key_name": key_name, "key_value": key_value})

        return information_disclosure



    def errback(self, f):
        self.log_error(f'请求失败: {f.request.url}')
