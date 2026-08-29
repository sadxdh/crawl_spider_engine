"""产品召回-吉林省监局，来源：https://scjgj.jl.gov.cn/zwgk/tzgg → product_recall"""
import hashlib, scrapy
from urllib.parse import urlencode

from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.decrypt import *

_C = lambda v: (v[0] if isinstance(v, list) and v else v or '').strip()


class JilinRecallSpider(BaseSpider):
    name = 'economy_recall_jilin'
    data_table = 'product_recall'
    allowed_domains = ['scjgj.jl.gov.cn']
    proxy_type = 'long_proxy'
    custom_settings = {'CONCURRENT_REQUESTS': 8, 'DOWNLOAD_DELAY': 0.3}
    dedup_fields = ['md5_value']
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Cache-Control': 'no-cache',
        'Content-Type': 'text/xml;charset=UTF-8',
        'Origin': 'http://www.jldpac.com',
        'Pragma': 'no-cache',
        'Referer': 'http://www.jldpac.com/modular/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    }

    def start_requests(self):
        for page in range(self.start_page, self.end_page + 1):
            # data  有问题，原本就是这样写的，调度任务也没有这个脚本
            # 无法知晓采集哪个列表
            data = decrypt_jilin_spider(page, call_func='gen_data')
            base_url = 'http://www.jldpac.com/honsanCloudAct'
            body = data.encode("unicode_escape")
            yield scrapy.Request(
                url=base_url,
                method="POST",
                headers=self.headers,
                body=body,
                callback=self.parse_list,
                errback=self.errback,
                dont_filter=True
            )

    def parse_list(self, response):
        result = decrypt_jilin_spider(response.text, call_func='decode')
        datas = result['results'][0]['args'][0]['data']['list']
        for data in datas:
            announcement_title = data['title']
            if '吉林' not in announcement_title:
                continue
            detail_id = data['id']
            pic_url = data['image']
            u2 = match_text(pic_url, r'base64(.*?)_image')
            detail_url = f'http://www.jldpac.com/honsanFileCatch/cloud.sys.tomcatV11/api/v1/template/getViewById_catch{u2}.json'
            announcement_url = f'http://www.jldpac.com/info/#/?t=47e6544fca0b47d79159b9b62a3a56ab&id={detail_id}'
            release_date = data['create_date'].split(' ')[0]
            entity_name = match_text(announcement_title, pattern=r'(.*?公司|.*?厂|.*?店).*召回')
            entity_name = entity_name.split('】')[1] if entity_name and '】' in entity_name else entity_name

            temp = {'announcement_title': announcement_title, 'announcement_url': announcement_url,
                    'release_date': release_date, 'entity_name': entity_name, 'detail_id': detail_id,
                    'detail_url': detail_url}
            params = {'templateId': '47e6544fca0b47d79159b9b62a3a56ab', 'id': detail_id}
            url = f'{detail_url}?{urlencode(params)}'
            yield scrapy.Request(
                url=url,
                method="POST",
                headers=self.headers,
                callback=self.parse_list,
                errback=self.errback,
                cb_kwargs={'params': temp},
            )

    def parse_detail(self, response, params):
        result = response.json()[0]
        content = result['content']

        announcement_title = params['announcement_title']
        release_date = params['release_date'].strip()
        entity_name = params['entity_name']
        items = {}
        if entity_name:
            md5_value = hash_md5(release_date + entity_name + announcement_title)
            items['md5_value'] = md5_value
            items['release_date'] = release_date
            items['entity_name'] = params['entity_name']
            items['announcement_title'] = announcement_title
            items['announcement_url'] = params['announcement_url']
            items['content'] = content
            items['source'] = '吉林省缺陷产品管理中心'
            self.log_info(items)
            yield items


    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
