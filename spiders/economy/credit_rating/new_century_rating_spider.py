"""新世纪资信评级爬虫 → entity_credit_rating"""
import hashlib, scrapy
from spiders.base_spider import BaseSpider
from utils.mysql_tools import select_data
from utils.tools import *

class NewCenturyRatingSpider(BaseSpider):
    name='economy_new_century_rating'
    data_table='entity_credit_rating'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cookie': 'menu_opennames=[%2251%22]; active_name=51; template_id=4; menu_id=3; page_id=51',
        'Host': 'www.shxsj.com',
        'Origin': 'http://www.shxsj.com',
        'Referer': 'http://www.shxsj.com/page?template=4&pageid=51&mid=3',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/126.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'lang': '',
        'token': '',
    }

    def start_requests(self):
        for cid, default_pages in {'51': 811, '61': 1705}.items():
            crawl_pages = default_pages if self.end_page < 0 else self.end_page
            for page in range(self.start_page, int(crawl_pages) + 1):
                get_list_from_data = {
                    'cid': cid,
                    'limit': '10',
                    'page': str(page),
                    'sort_val': '',
                    'sort_key': '',
                    'rank_stime': '',
                    'rank_etime': '',
                    'keyword': '',
                    'rank_type': '',
                    'main_type': '',
                    'rank_level': '',
                    'bound_type': '',
                }

                get_list_url = 'http://www.shxsj.com/serve/api/article_api/get_cid_article'

                yield scrapy.FormRequest(
                    url=get_list_url,
                    method='POST',
                    headers=self.headers,
                    formdata=get_list_from_data,
                    callback=self.parse_list,
                    dont_filter=True,
                )

    def parse_list(self, response):
        """解析列表页返回并判断数据库是否存在"""
        result = response.json()['data']['list']['data']
        for responses_json in result:
            if not responses_json['pdf']:
                continue
            page_id = responses_json['id']
            details_url = f'http://www.shxsj.com/page?template=8&pageid={page_id}&mid=3&listype=1'

            try:
                yield from self.parse_detail(responses_json, details_url)
            except Exception as e:
                error_msg = f'url: {details_url}, 新世纪资信,详情解析错误: {e}'
                self.log_error(error_msg)
                # send_dd_msg(self.spider_name, '解析失败', error_msg)

    def parse_detail(self, responses_json, details_url):
        """字段解析存储 & 文件处理"""
        pdf_href = responses_json['pdf'][0]['url']
        pdf_filename = pdf_href.split('/')[-1]
        pdffile_url = urljoin('http://www.shxsj.com', pdf_href)

        project_data = responses_json['project']
        project_name = project_data['issuer'].replace('"', '')
        entity_name = match_text(project_name, r'年(.*?公司)')
        rating_date = project_data.get('rank_time')
        entity_rating = project_data.get('main_type')
        debt_rating = project_data.get('bound_type')
        rating_outlook = project_data.get('rank_level')
        mysql_result = select_data(table='wentao_basedata.entity_info',
                                   data=['entity_id'],
                                   condition=f'entity_name = "{entity_name}";')

        entity_id = mysql_result[0]['entity_id'] if mysql_result else None

        md5_value = hash_md5(project_name + str(rating_date))
        items = {}
        items['md5_value'] = md5_value
        items['entity_id'] = entity_id
        items['entity_name'] = entity_name
        items['project_name'] = project_name
        items['rating_date'] = rating_date
        items['entity_rating'] = entity_rating
        items['debt_rating'] = debt_rating
        items['rating_outlook'] = rating_outlook
        items['rating_agency'] = '上海新世纪资信评估投资服务有限公司'
        items['url'] = details_url
        items['announcement_title'] = pdf_filename
        items['announcement_url'] = pdffile_url
        # insert_data(table='entity_credit_rating', data=item)
        yield items


    def errback(self,failure):self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
