"""百度百科人物 → entity_baidu_baike"""
import hashlib, scrapy
from lxml import etree
from spiders.base_spider import BaseSpider
from utils.mysql_tools import select_data
from utils.tools import *
from utils.db.yuncrawl_redis_opt import *
from utils.db.yuncrawl_mysql_opt import *


class BaiduBaikeSpider(BaseSpider):
    name = 'economy_baidu_baike'
    data_table = 'person_profile'
    dedup_fields = ['md5_value']
    default_end_page = 3

    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Referer': 'https://baike.baidu.com/item/%E9%99%88%E9%94%A6%E7%9F%B3/8760278',
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
    }

    def select_limit_data(self, offset, limit_num):
        """分页查询数据"""
        # counting_key = self.crawler.settings.get('YUNCRAWL_COUNTING_KEY')
        # key = counting_key % {'spider': self.name}
        #
        # offset = str_get(key)
        # offset = int(offset) if offset else 0
        #
        # sql = ('SELECT esh.entity_id, ei.entity_name, esh.staff_name '
        #        'FROM wentao_basedata.entity_staff_history esh '
        #        'JOIN  wentao_basedata.entity_info ei ON esh.entity_id = ei.entity_id '
        #        f'WHERE  ei.entity_type like "%有限%" LIMIT {limit_num} OFFSET {offset}')
        # datas = get_all(sql)
        # if datas:
        #     offset += limit_num
        #     str_set(key, offset)

        datas = select_data(
            table=(
                'wentao_basedata.entity_staff_history esh '
                'JOIN wentao_basedata.entity_info ei ON esh.entity_id = ei.entity_id'
            ),
            data=[
                'esh.entity_id',
                'ei.entity_name',
                'esh.staff_name',
            ],
            condition=f'ei.entity_type LIKE "%有限%" LIMIT {limit_num} OFFSET {offset}',
        )
        return datas

    def start_requests(self):
        datas = self.select_limit_data(int(self.start_page), int(self.end_page))
        for person_info in datas:
            person_name = person_info['staff_name']
            params = {'enc': 'utf8', 'wd': person_name}
            url = 'https://baike.baidu.com/api/searchui/suggest'
            yield scrapy.FormRequest(
                url,
                method='get',
                headers=self.headers,
                formdata=params,
                meta={'person_info': person_info},
                callback=self.parse,
            )

    def parse(self, response):
        person_info = response.meta['person_info']
        person_name = person_info['staff_name']
        result = response.json()
        datas = result['list']
        for data in datas:
            person_id = data['lemmaId']
            title = data['lemmaTitle']
            desc = data['lemmaDesc']
            self.log_info(f'person_name:{person_name} title: {title} desc:{desc}')
            meta_data = {'person_name': title, 'person_desc': desc}
            if title == person_name and ('公司' in desc or '法人' in desc or '董事' in desc or '合伙人' in desc):
                url = f'https://baike.baidu.com/item/{person_name}/{person_id}'
                yield scrapy.Request(
                    url,
                    headers=self.headers,
                    meta={'data': meta_data},
                    callback=self.parse_detail,
                )

    def parse_detail(self, response):
        meta = response.meta
        meta_data = meta['data']
        person_name = meta_data['person_name']
        person_desc = meta_data['person_desc']

        # pic_link = response.xpath('//div[@class="abstractAlbum_zx830"]/img/@src').get()
        pic_link = response.xpath('//meta[@property="og:image"]/@content').get()
        if 'baike.png' in pic_link:
            pic_link = None
        result = response.xpath('//div[contains(@class,"J-summary")]//text()').getall()
        summary = ''.join(result)
        summary = re.sub(r'\[.*?]', '', summary)

        items = {}
        items['person_name'] = person_name
        items['person_desc'] = person_desc
        items['summary'] = summary
        items['pic_link'] = pic_link
        items['md5_value'] = hash_md5(person_name + person_desc)
        yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
