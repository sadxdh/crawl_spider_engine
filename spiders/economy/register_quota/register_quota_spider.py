"""
DCM注册额度爬虫（entity_register_quota）
数据来源：银行间市场交易商协会 nafmii.org.cn

抓取11种债券类型的注册批准通知书：
  TDFI DFI cp mtn scp ppn abn zcdbgjcb prn gn smecn

增量策略：
  start_page=1 end_page=2（各类型前2页）
  去重字段：md5_value（title + release_date + approval_num 的 md5）

本地调试：
  scrapy crawl economy_register_quota -a start_page=1 -a end_page=2
"""
import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *


class RegisterQuotaSpider(BaseSpider):
    """银行间DCM注册额度爬虫"""

    name = 'economy_register_quota'
    data_table = 'entity_register_quota'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,'
                  '*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Referer': 'https://www.nafmii.org.cn/cpxl/zwrzgj/dcmzcfxtzs/DFI/index.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/127.0.0.0 Safari/537.36',
    }
    bond_type = ['TDFI', 'DFI', 'cp', 'mtn', 'scp', 'ppn', 'abn', 'zcdbgjcb', 'prn', 'gn', 'smecn']

    @staticmethod
    def generate_url(bond_type, page):
        base_url = 'https://www.nafmii.org.cn/cpxl/zwrzgj/dcmzcfxtzs/'
        if page == 0:
            url = f'{base_url}{bond_type}/index.html'
        else:
            url = f'{base_url}{bond_type}/index_{page}.html'
        return url

    def start_requests(self):
        for bond_type in self.bond_type:
            for page in range(self.start_page, self.end_page + 1):
                url = self.generate_url(bond_type, page)
                yield scrapy.Request(
                    url=url,
                    method='GET',
                    headers=self.headers,
                    callback=self.parse_list,
                )

    def parse_list(self, response):
        html_ele = etree.HTML(response.text.encode(response.encoding).decode())
        rows = html_ele.xpath('//div[@class="zlgz_list_con"]/ul/li')
        for row in rows:
            title = row.xpath('./a/@title')[0]
            href = row.xpath('./a/@href')[0]
            release_date = row.xpath('./div[@class="zlgz_list_time"]/text()')[0]
            url = urljoin(response.url, href)
            entity_name, approval_num = self.parse_title(title)

            items = {}
            items['entity_name'] = entity_name
            items['announcement_title'] = title
            items['announcement_url'] = url
            items['release_date'] = release_date
            items['register_approval_num'] = approval_num
            items['source'] = '银行间DCM'
            approval_num = approval_num if approval_num else ''
            items['md5_value'] = hash_md5(title+str(release_date)+approval_num)
            # insert_data('entity_register_quota', item)
            yield items

    @staticmethod
    def parse_title(title):
        entity_name_list = re.findall(r'号.*[(（](.*?公司)', title)
        approval_num_list = re.findall(r'-(中.*?号)|-(中.*?)（', title)
        entity_name = entity_name_list[0] if entity_name_list else None
        approval_num = ''.join(approval_num_list[0]) if approval_num_list else None
        return entity_name, approval_num



    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
