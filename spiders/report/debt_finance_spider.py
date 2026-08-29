"""银行间债务融资公告爬虫，来源：nafmii.org.cn"""
import json, hashlib, scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *

class DebtFinanceSpider(BaseSpider):
    name = 'report_debt_finance'
    # data_table = 'debt_finance_announcement'
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
        'Content-Type': 'application/json',
        'Origin': 'https://www.nafmii.org.cn',
        'Referer': 'https://www.nafmii.org.cn/xxpl/zwrzgjxxpl/fxdx/fxdfgg/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0',
        'X-Requested-With': 'XMLHttpRequest',
    }
    base_url = 'https://www.nafmii.org.cn/query/noticeDataQuy'
    detail_file_url = 'https://www.nafmii.org.cn/query/noticeFileQuy'
    detail_url = 'https://www.nafmii.org.cn/xxpl/zwrzgjxxpl/fxwj/202202/t20220218_199440.html?id={}&IS_NOTICE=1'
    file_url = 'https://nafmiiapp.cfae.cn/nafmii/app/nafmii-data-server/api/data/DcmFileDown/dcmDownloadfilesNew?publishId={}&fileMd5={}'
    detail_list = []
    channel = {
        '发行披露':
            {'category': ["发行文件", "申购说明", "招标文件", "其他与发行相关的事项"],
             'notice_type': ["01001", "01002", "01004", "01003"],
             'count_page': 13470},
        '发行结果': {'category': None, 'notice_type': ["02001", "02002", "02003"], 'count_page': 4476},
        '信用评级': {'category': ["主体评级", "债项评级"], 'notice_type': ["03001", "03002"], 'count_page': 2555},
        '财务报告': {
            'category': ["一季度财务报告", "半年度财务报告", "三季度财务报告", "年度报告及审计报告",
                         "财务报告延迟披露说明"],
            'notice_type': ["04001", "04002", "04003", "04004", "04005"], 'count_page': 6427},
        'ABN定期报告': {'category': None, 'notice_type': ["05001"], 'count_page': 563},
        '付息兑付': {
            'category': ["付息兑付公告", "风险提示公告", "信用增进履行情况公告", "违约公告", "违约后续进展公告",
                         "延期支付本息公告"],
            'notice_type': ["05001"], 'count_page': 8599},
        '重大事项及其他': {
            'category': ["重大事项（机构）", "重大事项（债项）", "中介机构专项意见（机构）", "中介机构专项意见（债项）"],
            'notice_type': ["07001", "07003", "07002", "07004"], 'count_page': 5195},
        '持有人会议': {
            'category': ["召开公告", "议案概要", "决议", "法律意见书", "相关机构答复", "其他"],
            'meet_type': ["0", "1", "2", "3", "4", "99"], 'count_page': 1239},
    }

    @staticmethod
    def generate_json_data(channel_1, channel_2, notice_type, meet_type, page):
        json_data = {
            'channelName': '',
            'channelParentNameList': [channel_1],
            'channelNameList': channel_2,
            'keys': [],
            'bond_': '',
            'publishWay': 'DCM',
            'notice_type': notice_type,
            'meet_type': meet_type,
            'searchWord': '',
            'start_time': '',
            'end_time': '',
            'page': page,
            'rows': 10,
            'type': '',
        }
        return json_data

    def start_requests(self):
        for channel_1, value in self.channel.items():
            channel_2 = value.get('category', [])
            notice_type = value.get('notice_type', [])
            meet_type = value.get('meet_type', [])
            count_page = value.get('count_page', 1)
            # 如果结束页小于0触发对历史数据的爬取
            end_page = count_page if int(self.end_page) < 0 else self.end_page
            for page in range(int(self.start_page), end_page + 1):
                json_data = self.generate_json_data(channel_1, channel_2, notice_type, meet_type, page)
                yield scrapy.Request(
                    url=self.base_url,
                    method="POST",
                    headers=self.headers,
                    body=json.dumps(json_data, separators=(",", ":"), ensure_ascii=False),
                    callback=self.parse_list,
                    dont_filter=True
                )

    def parse_list(self, response):
        response = response.json()
        result = response['data']['list']
        for data in result:
            level_name_1 = data['NOTICE_NAME1']
            level_name_2 = data['NOTICE_NAME']
            announcement_title = data['NOTICE_TITLE']
            announcement_date = data['CHECK_TIME']
            publish_id = data['PUBLISH_ID']
            announcement_url = self.detail_url.format(publish_id)
            md5_value = hash_md5(str(announcement_date) + announcement_title + str(publish_id))

            items = {}
            items['level_name_1'] = level_name_1
            items['level_name_2'] = level_name_2
            items['announcement_title'] = announcement_title
            items['announcement_date'] = announcement_date
            items['announcement_url'] = announcement_url
            items['md5_value'] = md5_value
            items['_table'] = 'debt_finance_announcement'
            # insert_data('debt_finance_announcement', item)
            yield items
            yield from self.get_detail({'publish_id': publish_id, 'announcement_md5_value': md5_value})

    def get_detail(self, data):
        publish_id = data['publish_id']
        # json_data = '{"PUBLISH_ID":"%s"}' % publish_id
        json_data = {
            "PUBLISH_ID": publish_id,
        }
        announcement_md5_value = data['announcement_md5_value']
        yield scrapy.Request(
            url=self.detail_file_url,
            method="POST",
            headers=self.headers,
            body=json.dumps(json_data, separators=(",", ":"), ensure_ascii=False),
            callback=self.parse_detail,
            cb_kwargs={"announcement_md5_value": announcement_md5_value},
            dont_filter=True,
        )


    def parse_detail(self, response, announcement_md5_value):
        response = response.json()
        result = response['data']
        publish_id = result['ID']
        files = result['files']
        for data in files:
            attachment_title = data['FILE_NAME']
            file_id = data['FILE_ID']
            attachment_url = self.file_url.format(publish_id, file_id)
            attachment_type = '票据募集' if '票据募集' in attachment_title else None

            md5_value = hash_md5(announcement_md5_value + attachment_title)

            items = {}
            items['announcement_md5_value'] = announcement_md5_value
            items['attachment_title'] = attachment_title
            items['attachment_url'] = attachment_url
            items['attachment_type'] = attachment_type
            items['md5_value'] = md5_value
            items['_table'] = 'debt_finance_announcement_mapping'
            # insert_data('debt_finance_announcement_mapping', item)
            yield items


    def errback(self, failure): self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
