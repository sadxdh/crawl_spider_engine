import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *

class IpoDeclareHkexSpider(BaseSpider):
    name = 'ipo_declare_hkex'
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
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'content-type': 'application/json',
        'priority': 'u=1, i',
        'referer': 'https://www1.hkexnews.hk/app/appindex.html?lang=zh',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Microsoft Edge";v="133", "Chromium";v="133"',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
    }
    req_info = {
        '已递表': 'https://www1.hkexnews.hk/ncms/json/eds/appactive_app_sehk_c.json',
        '通过聆讯': 'https://www1.hkexnews.hk/ncms/json/eds/appactive_appphip_sehk_c.json',
        '没有进展': 'https://www1.hkexnews.hk/ncms/json/eds/appinactive_sehk_c.json',
        '已上市': 'https://www1.hkexnews.hk/ncms/json/eds/applisted_sehk_c.json',
        '被发回': 'https://www1.hkexnews.hk/ncms/json/eds/appreturned_sehk_c.json'
    }
    ipo_status = {'RJ': '被拒绝', 'LP': '失效', 'W': '撤回'}

    def start_requests(self):
        for ipo_type, url in self.req_info.items():
            yield scrapy.Request(
                url=url,
                callback=self.get_list,
                headers=self.headers,
                cb_kwargs={"ipo_type": ipo_type},
            )

    def get_list(self, response, ipo_type):
        try:
            parse_result = []
            if ipo_type == '已递表':
                parse_result = self.parse_list_1(response)
            if ipo_type == '通过聆讯':
                parse_result = self.parse_list_2(response)
            if ipo_type == '没有进展':
                parse_result = self.parse_list_3(response)
            if ipo_type == '已上市':
                parse_result = self.parse_list_4(response)
            if ipo_type == '被发回':
                parse_result = self.parse_list_5(response)
            yield from self.save_data(parse_result)
        except Exception as e:
            msg = f'url: {response.url} 披露易ipo-{ipo_type}列表解析错误：{e}'
            self.log_error(msg)
            # send_dd_msg(self.spider_name, '解析失败', msg)

    def save_data(self, datas):
        for data in datas:
            entity_id = data.get('entity_id')
            entity_name = data.get('entity_name')
            declare_info = data.get('declare_info')
            declare_date = data.get('declare_date')
            ipo_status = data.get('ipo_status', '')
            update_date = data.get('update_date')
            prospectus = data.get('prospectus')
            sponsor = data.get('sponsor')
            md5_value = hash_md5(entity_name+ipo_status+update_date)

            items1 = {}
            items1['entity_id'] = entity_id
            items1['entity_name'] = chinese_traditional_to_simplified(entity_name)
            items1['declare_info'] = declare_info
            items1['declare_date'] = declare_date
            items1['listing_sector'] = '主板'
            items1['ipo_status'] = ipo_status
            items1['update_date'] = update_date
            items1['prospectus'] = prospectus
            items1['sponsor'] = sponsor
            items1['md5_value'] = md5_value
            # insert_data(table='entity_ipo_declare_hk_shares', data=item)
            items1['_table'] = 'entity_ipo_declare_hk_shares'
            yield items1

            # 保存附件
            attachment_data = data.get('attachment_data', [])
            for attach in attachment_data:
                attachment_title = attach['attachment_title']
                attachment_url = attach['attachment_url']
                attachment_date = attach['attachment_date']
                attach_md5_value = hash_md5(attachment_title+attachment_url+attachment_date)

                items2 = {}
                items2['ipo_md5_value'] = md5_value
                items2['attachment_title'] = chinese_traditional_to_simplified(attachment_title)
                items2['attachment_url'] = attachment_url
                items2['publish_date'] = attachment_date
                items2['md5_value'] = attach_md5_value
                # insert_data('entity_ipo_declare_hk_shares_mapping', data=item)
                items2['_table'] = 'entity_ipo_declare_hk_shares_mapping'
                yield items2

    def parse_list_1(self, response):
        # 已递表
        result = response.json()['app']
        temp_list = []
        for res in result:
            entity_name = res['a']
            update_date = trans_en_date(res['d'], '%d/%m/%Y')
            ipo_status = '已递表'
            attachments = res['ls']
            attachment_data = self.parse_attachment(attachments)

            temp = {'entity_name': entity_name, 'update_date': update_date, 'ipo_status': ipo_status,
                    'attachment_data': attachment_data}
            temp_list.append(temp)
        return temp_list

    def parse_list_2(self, response):
        result = response.json()['app']
        temp_list = []
        for res in result:
            entity_name = res['a']
            update_date = trans_en_date(res['d'], '%d/%m/%Y')
            ipo_status = '通过聆讯'
            attachments = res['ls']
            attachment_data = self.parse_attachment(attachments)

            temp = {'entity_name': entity_name, 'update_date': update_date, 'ipo_status': ipo_status,
                    'attachment_data': attachment_data}
            temp_list.append(temp)
        return temp_list

    def parse_list_3(self, response):
        result = response.json()['app']
        temp_list = []
        for res in result:
            entity_name = res['a']
            update_date = trans_en_date(res['d'], '%d/%m/%Y')
            ipo_status = self.ipo_status.get(res['s'])
            temp = {'entity_name': entity_name, 'update_date': update_date, 'ipo_status': ipo_status}
            temp_list.append(temp)
        return temp_list

    @staticmethod
    def parse_list_4(response):
        # 已上市
        result = response.json()['app']
        temp_list = []
        for res in result:
            entity_id = res['st']
            entity_name = res['a']
            update_date = trans_en_date(res['d'], '%d/%m/%Y')
            ipo_status = '已上市'
            temp = {'entity_id': entity_id, 'entity_name': entity_name, 'update_date': update_date,
                    'ipo_status': ipo_status}
            temp_list.append(temp)
        return temp_list

    @staticmethod
    def parse_list_5(response):
        result = response.json()['app']
        temp_list = []
        for res in result:
            # 申请人
            entity_name = res['a']
            # 发回日期
            update_date = trans_en_date(res['rd'], '%d/%m/%Y')
            # 保荐人
            sponsor = res['s']
            temp = {'entity_name': entity_name, 'update_date': update_date, 'sponsor': sponsor}
            temp_list.append(temp)
        return temp_list

    def parse_attachment(self, attachments):
        # 解析附件链接
        attachment_data = []
        for ls in attachments:
            pre_url = 'https://www1.hkexnews.hk/app/'
            attachment_title = ls.get('nF') if ls.get('nF') else ls['nS1']
            href = ls['u1']
            attachment_url = urljoin(pre_url, href)
            attachment_date = trans_en_date(ls['d'], '%d/%m/%Y')
            temp = {'attachment_title': attachment_title, 'attachment_url': attachment_url,
                    'attachment_date': attachment_date}
            attachment_data.append(temp)
            logger.info(f'附件信息数据：{temp}')
        return attachment_data

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')