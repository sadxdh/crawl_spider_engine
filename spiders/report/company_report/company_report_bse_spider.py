import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class CompanyReportBseSpider(BaseSpider):
    name = 'company_report_bse_spider'
    data_table = 'entity_announcement'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'text/javascript, application/javascript, application/ecmascript, '
                  'application/x-ecmascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://www.bse.cn',
        'Referer': 'https://www.bse.cn/disclosure/announcement.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0',
        'X-Requested-With': 'XMLHttpRequest',
    }
    domain = 'https://www.bse.cn/'
    base_url = 'https://www.bse.cn/disclosureInfoController/companyAnnouncement.do'
    cate_url = 'https://www.bse.cn/disclosureInfoController/disclosure_type.do'


    def start_requests(self):
        params = {'type': '6'}
        request_url = f'{self.cate_url}?{urlencode(params)}'
        yield scrapy.Request(
            url=request_url,
            method='GET',
            headers=self.headers,
            callback=self.get_cate_type,
            dont_filter=True,
        )

    @staticmethod
    def generate_data(page, cate_type):
        data = {
            'disclosureSubtype[]': cate_type,
            'page': str(page),
            'companyCd': '',
            'isNewThree': '1',
            'startTime': '2025-04-01',
            'endTime': '2025-06-31',
            'keyword': '',
            'xxfcbj[]': '2',
            'needFields[]': [
                'companyCd',
                'companyName',
                'disclosureTitle',
                'disclosurePostTitle',
                'destFilePath',
                'publishDate',
                'xxfcbj',
                'destFilePath',
                'fileExt',
                'xxzrlx',
            ],
            'sortfield': 'xxssdq',
            'sorttype': 'asc',
        }
        return data

    def get_cate_type(self, response):
        result = re.findall(r'null\(\[(.*?)]\)$', response.text)
        if result:
            res = json.loads(result[0])
            datas = res['values']
            for data in datas:
                cate_name = data['name']
                if '全部' in cate_name:
                    continue
                cate_type = data['dvalue'].split(':')[1].split(',')
                for page in range(int(self.start_page), int(self.end_page) + 1):
                    json_data = self.generate_data(page, cate_type)
                    yield scrapy.FormRequest(
                        url=self.base_url,
                        method='POST',
                        headers=self.headers,
                        formdata=json_data,
                        callback=self.parse_list,
                        dont_filter=True,
                        cb_kwargs={'cate_name': cate_name}
                    )

    def parse_list(self, response, cate_name):
        result = response.text
        res = re.findall(r'null\(\[(.*?)]\)$', result)
        if res:
            res = json.loads(res[0])
            datas = res['listInfo']['content']
            for row in datas:
                publish_time = row['publishDate']
                announcement_title = row['disclosureTitle']
                href = row['destFilePath']
                announcement_url = urljoin(self.domain, href)
                security_code = row['companyCd']
                security_short = row['companyName']

                source = '北交所'
                md5_value = hash_md5(str(publish_time)+announcement_title+security_code)

                items = {}
                items['publish_time'] = publish_time
                items['announcement_title'] = announcement_title
                items['announcement_url'] = announcement_url
                items['announcement_type'] = cate_name
                items['security_code'] = security_code
                items['security_short'] = security_short
                items['source'] = source
                items['md5_value'] = md5_value
                # insert_data(table='entity_announcement', data=item)
                yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')