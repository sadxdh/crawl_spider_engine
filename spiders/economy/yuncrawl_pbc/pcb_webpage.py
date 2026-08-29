import aiohttp
from scrapy.http import HtmlResponse
from scrapy.http import Request as ScrapyRequest
from utils.file_kit import *
from web_poet.pages import WebPage


async def make_async_request_scrapy_response(*args, **kwargs):
    async with aiohttp.ClientSession() as session:
        method = kwargs.pop('method', 'GET')
        async with session.request(method=method, *args, **kwargs) as response:
            content = await response.read()

            return HtmlResponse(
                url=str(response.url),
                body=content,
                encoding="utf-8",
                request=ScrapyRequest(*args, **kwargs),
                status=response.status
            )

class PbcListPage(WebPage):

    # 人民银行 页面对象
    def parse_list(self, conf):
        rows_xpath = conf.get('rows_xpath')
        title_xpath = conf.get('title_xpath') or './/td[@class="hei12jj"]//a/@title'
        href_xpath = conf.get('href_xpath') or './/td[@class="hei12jj"]//a/@href'
        time_xpath = conf.get('release_xpath') or './/td[@class="hei12jj"][2]/text()'

        rows = self.xpath(rows_xpath)
        temps = []
        for row in rows:
            title = row.xpath(title_xpath).get()
            href = row.xpath(href_xpath).get()
            release_time = row.xpath(time_xpath).get()
            url = self.response.urljoin(href)
            temp = {"title": title, "url": url, "release_time": release_time}
            temps.append(temp)
        return temps


class PcbDetailPage(WebPage):
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,'
                  '*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0',
    }

    async def parse_detail(self, conf):
        content_xpath = conf.get('content_xpath')
        href_xpath = conf.get('content_href_xpath')

        text_list = []
        if href_xpath:
            href = self.xpath(href_xpath).get()
            url = self.response.urljoin(href)
            response = await make_async_request_scrapy_response(url=url, headers=self.headers)
            content = response.body
            text_list = []
            if '.doc' in url:
                if str(url).endswith('.doc'):
                    content = convert_doc_to_docx(content)
                list1 = extract_docx_text(content)
                list2 = extract_docx_table(content)
                text_list = list1 + list2

            if '.xls' in url:
                text_list = extract_xlsx_text(content, output_format='string')

            if '.pdf' in url:
                list1 = extract_pdf_text(content)

                list2 = []
                tables = extract_pdf_table(content)
                for table in tables:
                    for row in table:
                        temp = ' '.join(cell for cell in row if cell)
                        list2.append(temp)
                text_list = list1 + list2

        if content_xpath:
            result = self.xpath(content_xpath).getall()
            if result:
                text_list = result

        text = ' '.join(text_list)
        return {'content': text}
