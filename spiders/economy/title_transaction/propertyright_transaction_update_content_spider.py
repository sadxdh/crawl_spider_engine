import platform
from spiders.base_spider import BaseSpider
from spiders.economy.title_transaction.common_function import *
from utils.tools import *
import asyncio
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright

class PropertyrightTransactionUpdateContentSpider(BaseSpider):
    name = 'propertyright_transaction_update_content'
    data_table = 'entity_propertyright_transaction'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'
    playwright_executor = ThreadPoolExecutor(max_workers=1)

    style = """
                <style> 
                    table {
                        width: 100%;
                        table-layout: fixed;
                        border-left: 1px solid #ddd;
                        border-top: 1px solid #ddd;
                    }

                    th, td {
                        border-right: 1px solid #ddd;
                        border-bottom: 1px solid #ddd;
                        overflow: auto;
                        vertical-align: middle;
                        text-align: left;
                        padding: 12px 0;
                        padding-left: 12px;
                        font-size: 14px;
                    }

                    th {
                        font-weight: normal;
                    }

                    .auditunit, .objectboss, .holdername, .objectname, .company_class{
                        color: #3849F7;
                    }

                 </style>
            """
    replace_company_name = '''<a id="company_id" class="company_class">{}
            <span class="companyId" style="display: none;">{}</span></a>'''
    replace_object_boss = '<span class="objectbossId" style="display: none;">{}</span>{}'
    replace_holder_name = '<span class="holdernameId" style="display: none;">{}</span>{}'
    replace_audit_unit = '<span class="auditunitId" style="display: none;">{}</span>{}'

    def start_requests(self):
        datas = get_none_content(self.data_table, int(self.end_page))
        for index, data in enumerate(datas):
            source = data['source']
            node_xpath = HTML_NODE_XPATH.get(source[:2])

            if '北京产权交易所' in source:
                yield from self.bj_transaction(data, index)
            else:
                yield from self.common_transaction(data, index, **node_xpath)


    def bj_transaction(self, data, index):
        # 北京交易所
        file_url = data['file_url']
        md5_value = data['md5_value']
        transferee_id = data['transferee_id']
        transferee = data['transferee']
        self.log_info(f'正在执行第{index}个 file_url:{file_url}')
        try:
            # # playwright 解决加速乐加密
            # response1, cookie_jar = playwright_request(self.browser, file_url)
            # cookies = JiaSuLe.encrypt_ck_2(response1, cookie_name='__jsl_clearance_s')
            # for cookie in cookie_jar:
            #     if cookie['name'] == '__jsl_clearance_s':
            #         cookie['value'] = cookies['__jsl_clearance_s']
            # response, cookie_ = playwright_request(self.browser, file_url, cookie=cookie_jar)
            response = get_jsl_cookies(url=file_url, proxies_type=True).text

            # 处理html中不需要的东西
            html_node_code = get_node_html(response,
                                           content_xpath='//div[@class="main-box"]',
                                           rm_node_xpath=['//p[contains(@class, "projects-messages")]'],
                                           rm_href_xpath='//ul/li/a[@href]',
                                           replace_node_xpath='//table')

            html_text = ''.join([self.style, html_node_code])
            if transferee:
                html_text = re.sub(transferee, self.replace_company_name.format(transferee, transferee_id), html_text)

            # 需要替换内容的xpath
            xpath_content_list = ['//td[@class="objectboss"]/text()',
                                  '//td[@class="holdername"]/text()',
                                  '//td[@class="auditunit"]/text()']

            yield from self.update_content(response, html_text, xpath_content_list, md5_value)
        except Exception as e:
            self.log_error(e)

    def update_content(self, response, html_text, xpath_content_list, md5_value):
        result = etree.HTML(response)

        for xpath_content in xpath_content_list:
            parse_res = xpath_parse(result, xpath_content, return_list=True)
            self.log_info(f'xpath解析结果：{parse_res}')
            if not parse_res:
                continue
            for res in parse_res:
                if 'boss' in xpath_content:
                    person_id = query_person_id(res)
                    html_text = re.sub(res, self.replace_object_boss.format(person_id, res), html_text)
                if 'unit' in xpath_content:
                    unit_id = query_entity_id(entity_name=res)
                    html_text = re.sub(res, self.replace_audit_unit.format(unit_id, res), html_text)
                if 'holder' in xpath_content:
                    holder_id = query_person_id(res) if len(res) <= 3 else query_entity_id(res)
                    if holder_id:
                        html_text = re.sub(res, self.replace_holder_name.format(holder_id, res), html_text)

        data = {'md5_value': md5_value, 'content': html_text}
        # update_data(TITLE_TRANSACTION, data)
        yield data


    def common_transaction(self, data, index, **kwargs):
        file_url = data['file_url']
        md5_value = data['md5_value']
        transferee_id = data['transferee_id']
        transferee = data['transferee']
        source = data['source']
        logger.warning(f'正在执行第{index}个 file_url:{file_url}')

        if '产投数据' in source:
            cookies = get_cookies()
            cookie_jar = cookie_to_cookieJar(cookies, domain=".cspea.com.cn")
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
            }
        else:
            cookie_jar = None
            headers = None

        try:
            proxy = ScrapyProxy.get_long_proxy()
            proxy = {"server": proxy}
            response, _ = self.playwright_fetch(
                file_url,
                cookie=cookie_jar,
                headers=headers,
                proxy=proxy,
            )
            html_node_code = get_node_html(response,
                                           content_xpath=kwargs.get('content_xpath'),
                                           clear_font_style=kwargs.get('clear_font_style'),
                                           rm_node_xpath=kwargs.get('rm_node_xpath'),
                                           rm_href_xpath=kwargs.get('rm_href_xpath'),
                                           replace_href_xpath=kwargs.get('replace_href_xpath'),
                                           replace_node_xpath=kwargs.get('replace_node_xpath'),
                                           replace_src_xpath=kwargs.get('replace_src_xpath')
                                           )
            html_text = ''.join([self.style, html_node_code])
            if transferee:
                html_text = re.sub(transferee, self.replace_company_name.format(transferee, transferee_id), html_text)
            yield from self.update_content(response, html_text, xpath_content_list=[], md5_value=md5_value)
        except Exception as e:
            self.log_error(e)

    def playwright_fetch(self, url, cookie=None, headers=None, proxy=None):
        def run():
            system_name = platform.system().lower()

            if system_name == "windows":
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

            launch_kwargs = {
                "headless": True,
            }

            if system_name == "linux":
                launch_kwargs["args"] = [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ]

            with sync_playwright() as driver:
                browser = driver.chromium.launch(**launch_kwargs)
                try:
                    return playwright_request(
                        browser,
                        url,
                        cookie=cookie,
                        headers=headers,
                        proxy=proxy,
                    )
                finally:
                    browser.close()

        return self.playwright_executor.submit(run).result()

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')