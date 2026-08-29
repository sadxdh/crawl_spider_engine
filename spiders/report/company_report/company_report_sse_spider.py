import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *
from utils.mysql_tools import select_data

class CompanyReportSseSpider(BaseSpider):
    name = 'company_report_sse_spider'
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
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://www.sse.com.cn/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0',
    }
    domain = 'https://www.sse.com.cn/'
    base_url = 'https://query.sse.com.cn/security/stock/queryCompanyBulletinNew.do'
    announce_type = [
        {'type_name': '定期报告', 'type_code': '00,0101,0102,0104,0103'},
        {'type_name': '董事会和监事会', 'type_code': '01'},
        {'type_name': '股东大会', 'type_code': '02'},
        {'type_name': '应当披露的交易', 'type_code': '03'},
        {'type_name': '首次公开发行', 'type_code': '08'},
        {'type_name': '关联交易', 'type_code': '25'},
        {'type_name': '对外担保', 'type_code': '09'},
        {'type_name': '募集资金使用与管理', 'type_code': '10'},
        {'type_name': '业绩预告、业绩快报和盈利预测', 'type_code': '11'},
        {'type_name': '利润分配和资本公积金转增股本', 'type_code': '12'},
        {'type_name': '股票交易异常波动和澄清', 'type_code': '13'},
        {'type_name': '股份上市流通与股本变动', 'type_code': '14'},
        {'type_name': '股东增持或减持股份', 'type_code': '15'},
        {'type_name': '权益变动报告书和（要约）收购', 'type_code': '16'},
        {'type_name': '股权型再融资', 'type_code': '17'},
        {'type_name': '其他再融资', 'type_code': '18'},
        {'type_name': '重大资产重组', 'type_code': '19'},
        {'type_name': '吸收合并', 'type_code': '20'},
        {'type_name': '回购股份', 'type_code': '21'},
        {'type_name': '可转换公司债', 'type_code': '22'},
        {'type_name': '股权激励及员工持股计划', 'type_code': '24'},
        {'type_name': '诉讼和仲裁', 'type_code': '26'},
        {'type_name': '股东股份被质押冻结或司法拍卖', 'type_code': '27'},
        {'type_name': '破产与重整', 'type_code': '28'},
        {'type_name': '其他重大事项', 'type_code': '29'},
        {'type_name': '公司重要基本信息变化', 'type_code': '30'},
        {'type_name': '风险警示', 'type_code': '31'},
        {'type_name': '暂停、恢复和终止上市', 'type_code': '32'},
        {'type_name': '补充更正公告', 'type_code': '33'},
        {'type_name': '规范运作', 'type_code': '34'},
        {'type_name': '中介机构报告', 'type_code': '35'},
        {'type_name': '停复牌提示性公告', 'type_code': '36'},
        {'type_name': '优先股', 'type_code': '37'},
        {'type_name': '特别表决权', 'type_code': '04'},
        {'type_name': '超额配售选择权', 'type_code': '05'},
        {'type_name': '存托凭证相关公告', 'type_code': '07'},
        {'type_name': '询价转让及配售', 'type_code': '06'},
        {'type_name': '境内外同步披露', 'type_code': '38'},
        {'type_name': '其他', 'type_code': '90'}]

    @staticmethod
    def get_security_code():
        datas = select_data(table='listing_info', data=['share_code'], condition='listed_exchange="上海证券交易所"')
        return datas

    @staticmethod
    def generate_params(security_code, page):
        params = {
            'isPagination': 'true',
            'pageHelp.pageSize': '10',
            'pageHelp.cacheSize': '1',
            'pageHelp.pageNo': page,
            'pageHelp.beginPage': page,
            'pageHelp.endPage': page,
            'START_DATE': '',
            'END_DATE': '',
            'SECURITY_CODE': security_code,
            'TITLE': '',
            'BULLETIN_TYPE': '',
        }
        return params

    @staticmethod
    def generate_params2(type_code, page):
        params = {
            'isPagination': 'true',
            'pageHelp.pageSize': '25',
            'pageHelp.cacheSize': '1',
            # 'START_DATE': date_through(-30),
            'START_DATE': '2025-04-01',
            'END_DATE': date_through(0),
            'SECURITY_CODE': '',
            'TITLE': '',
            'BULLETIN_TYPE': type_code,
            'stockType': '',
            'pageHelp.pageNo': page,
            'pageHelp.beginPage': page,
            'pageHelp.endPage': page,
        }
        return params

    def start_requests(self):
        for type_data in self.announce_type:
            type_code = type_data['type_code']
            for page in range(self.start_page, self.end_page + 1):
                params = self.generate_params2(type_code, page)
                separator = '&' if '?' in self.base_url else '?'
                request_url = f'{self.base_url}{separator}{urlencode(params)}'

                yield scrapy.Request(
                    url=request_url,
                    method='GET',
                    headers=self.headers,
                    callback=self.parse_list,
                    dont_filter=True,
                )

    def parse_list(self, response):
        result = response.json().get('result')
        if result:
            for row in result:
                for data in row:
                    publish_date = data['SSEDATE']
                    title = data['TITLE']
                    file_href = data['URL']
                    file_url = urljoin(self.domain, file_href)
                    file_type = data['BULLETIN_TYPE_DESC']
                    security_code = data['SECURITY_CODE']
                    security_short = data['SECURITY_NAME']
                    source = '上交所'
                    md5_value = hash_md5(str(publish_date) + title + security_code)

                    items = {}
                    items['publish_time'] = publish_date
                    items['announcement_title'] = title
                    items['announcement_url'] = file_url
                    items['announcement_type'] = file_type
                    items['security_code'] = security_code
                    items['security_short'] = security_short
                    items['source'] = source
                    items['md5_value'] = md5_value
                    # insert_data(table='entity_announcement', data=item)
                    yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')