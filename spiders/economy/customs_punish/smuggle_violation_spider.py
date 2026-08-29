import hashlib, scrapy
from urllib.parse import urlencode
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.time_kit import *
from spiders.economy.customs_punish.conf import inspection_quarantine, smuggle_violation, intellectual_property
from utils.ruishu.rs_crawler import RsRequest


# 海关走私违规行政处罚案件
class CustomsPunishSmuggleViolationSpider(BaseSpider):
    name = 'customs_punish_smuggle_violation'
    data_table = 'customs_punish'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0',
    }
    region_name = 'all'
    rs_reqs = RsRequest()

    @staticmethod
    def query_website(website_list, region_name='all'):
        if region_name == 'all':
            return website_list
        else:
            result = [i for i in website_list if region_name in i['web_name']]
            return result

    def start_requests(self):
        website_list = self.query_website(smuggle_violation, region_name=self.region_name)
        for website_data in website_list:
            yield from self.run(website_data)

    def run(self, website_data):
        list_url, total_page = self.get_paging(website_data)
        if total_page == 0:
            # 列表页只有一页
            api_url = website_data['api_url']
            detail_list =  self.get_info_data(page=1, list_url=api_url, data=website_data)
            yield from self.get_detail_list(detail_list)

        if list_url and total_page:
            end_page = total_page if int(self.end_page) < 0 else int(self.end_page)
            pages = [page for page in range(int(self.start_page), int(end_page) + 1)]

            for page in pages:
                list_url = re.sub(r'currentPage=.*?\d+&', f'currentPage={page}&', list_url)
                detail_list =  self.get_info_data(page, list_url, website_data)
                yield from self.get_detail_list(detail_list)

    def get_paging(self, data):
        """获取总页数"""
        api_url = data['api_url']
        response = self.rs_reqs.rs_request(api_url, headers=self.headers)
        if response:
            try:
                list_url, total_page = self.parse_paging(response)
                return list_url, total_page
            except Exception as e:
                msg = f'列表页的url解析错误, e:{e}, api_url: {api_url}'
                self.log_error(msg)
                # send_dd_msg(self.spider_name, '解析失败', msg)
        return None, None

    def parse_paging(self, response):
        result = response.text.encode(response.encoding).decode('utf-8')
        res = etree.HTML(result)
        # 解析尾页的链接，以yes结尾
        link_xpath = '//div[@class="gg_page"]/div//a[@title="尾页"]/@tagname | //div[@class="easysite-page-wrap"]//a[@title="尾页"]/@tagname'
        link_href = xpath_parse(res, xpath_content=link_xpath)
        total_page = 2  # 总页数默认为2页

        if 'LASTPAGE' in link_href:
            # 只有一页
            return response.url, 0

        if link_href.endswith('.html'):
            # 新链接以.html结尾, 解析跳转下的内容
            xpath_content = '//div[@class="easysite-jump-page"]/input/@onkeydown'
            jump_link = xpath_parse(res, xpath_content)
            link_href = match_text(jump_link, r'(/eportal.*?)\|\|')
            total_page = xpath_parse(res, '//input[@totalpage]/@totalpage')

        if link_href.endswith('yes'):
            total_page = match_text(link_href, r'currentPage=(.*?)&')

        list_url = urljoin(response.url, link_href)
        return list_url, total_page


    def get_info_data(self, page, list_url, data):
        """解析列表数据"""
        api_url, web_name, punish_type = data['api_url'], data['web_name'], data['punish_type']
        self.log_info(f'当前海关：{web_name} 当前页数:{page} 列表信息正在执行 list_url:{list_url}')
        temp = {'punish_type': punish_type, 'domain': api_url, 'web_name': web_name}
        response = self.rs_reqs.rs_request(list_url, headers=self.headers)
        if response:
            try:
                parse_result = self.parse_info_data(response)
                return [{**temp, **i} for i in parse_result]
            except Exception as e:
                msg = f'网站列表信息解析错误, e:{e}, api_url:{list_url}'
                self.log_error(msg)
                # send_dd_msg(self.spider_name, '解析失败', msg)

    def parse_info_data(self, response):
        detail_list = []
        result = etree.HTML(response.text.encode(response.encoding).decode('utf-8'))
        li_list = xpath_parse(result, '//ul[@class="conList_ul"]/li[a]', return_list=True)
        if li_list:
            for li in li_list:
                publish_date = xpath_parse(li, './span/text()')
                title = xpath_parse(li, './a/@title')
                if '近期无更新' in title or '更新情况' in title:
                    continue
                href = xpath_parse(li, './a/@href')
                entity_name = match_text(title, r'对(.*?公司)|关于(.*?公司)')
                case_num = match_text(title, r'（(.*?号)）')
                temp = {
                    'publish_date': publish_date,
                    'title': title,
                    'href': href,
                    'entity_name': entity_name,
                    'case_num': case_num,
                }
                self.log_info(f'列表解析结果, temp:{temp}')
                detail_list.append(temp)
        return detail_list

    def get_detail_list(self, detail_list):
        for data in detail_list:
            yield from self.get_detail(data)

    def get_detail(self, data):
        """获取文件详情"""
        domain = data['domain']
        href = data['href']
        url = urljoin(domain, href)
        logger.warning(f'详情信息正在执行 detail_url:{url}')

        # 列表页有文件
        if '.pdf' in url or '.doc' in url or '.xls' in url or '.jpg' in url:
            temp = {'announcement_title': data['title'], 'announcement_url': url}
            datas = data | temp
            data_data1 = self.save_data(datas)
            yield data_data1

        if '.htm' in url:
            response = self.rs_reqs.rs_request(url, headers=self.headers)
            if response:
                try:
                    temp_list = self.parse_detail(response, domain)
                    datas = [{**data, **i} for i in temp_list]
                    data_data2 = self.save_data(datas)
                    yield data_data2
                except Exception as e:
                    msg = f'详情页解析错误, e:{e}, url:{url}'
                    self.log_error(msg)
                    # send_dd_msg(self.spider_name, '解析失败', msg)

    def save_data(self, datas):
        for data in datas:
            title = data['title']
            publish_date = data['publish_date']
            announcement_title = data['announcement_title']
            items = {}
            items['publish_date'] = publish_date
            items['title'] = title
            items['punish_type'] = data['punish_type']
            items['entity_name'] = data['entity_name']
            items['case_num'] = data['case_num']
            items['announcement_title'] = announcement_title
            items['announcement_url'] = data['announcement_url']
            items['md5_value'] = hash_md5(title + publish_date + announcement_title)
            items['web_name'] = data['web_name']
            items['oss_url'] = data.get('oss_url')
            # insert_data('customs_punish', data=item)
            return items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')