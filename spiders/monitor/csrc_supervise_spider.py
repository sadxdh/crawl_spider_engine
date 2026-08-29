"""证监会-行政许可/行政处罚 → enterprise_dynamics
参照旧项目 yuncrawl GovCsrcSpider: searchList API + JSON 响应
"""
import scrapy
from spiders.base_spider import BaseSpider
from utils.tools import *
from utils.file_kit import *

class CsrcSuperviseSpider(BaseSpider):
    name = 'economy_csrc_supervise'
    data_table = 'enterprise_dynamics'
    dedup_fields = ['md5_value']
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "sec-ch-ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    def start_requests(self):
        pages = [page for page in range(self.start_page, self.end_page + 1)]

        url_list = [
            'http://www.csrc.gov.cn/searchList/768f924c237f41b5921f6d0e4db0e8b5',  # 行政许可批复
            'http://www.csrc.gov.cn/searchList/17d5ff2fe43e488dba825807ae40d63f',  # 行政处罚决定
            'http://www.csrc.gov.cn/searchList/3795869930ca4b70bf55469270a6e641',  # 市场进入决定
            'http://www.csrc.gov.cn/searchList/3ff8b60a78ab4c749387d99b9164ec6e',  # 监管措施
            'http://www.csrc.gov.cn/searchList/6d9911d05b33485c8a0264a5fcafa578',  # 行政执法当事人承诺
            'http://www.csrc.gov.cn/searchList/77f99322f83040edb548974091db3f8b',  # 行政复议
            'http://www.csrc.gov.cn/searchList/c0911905365c4b88ba8b264cee6378d9',  # 备案管理
        ]

        for url in url_list:
            for page in pages:
                params = {
                    '_isAgg': 'true',
                    '_isJson': 'true',
                    '_pageSize': '10',
                    '_template': 'index',
                    '_rangeTimeGte': '',
                    '_channelName': '',
                    'page': str(page),
                }
                yield scrapy.FormRequest(
                    url,
                    method='get',
                    formdata=params,
                    dont_filter=True,
                    callback=self.parse,
                    headers=self.headers
                )

    def parse(self, response, *args, **kwargs):
        rows = response.json()['data']['results']
        for row in rows:
            title = row.get('title')
            url = row.get('url')
            if 'http' not in url:
                url = 'http:' + url
            release_time = row.get('publishedTimeStr')
            content = row.get('content')
            website_name = '中国证券监督管理委员会'
            if content:
                items = {}
                items['release_time'] = release_time
                items['title'] = title
                items['url'] = url
                items['content'] = content
                items['webname'] = website_name
                items['md5_value'] = hash_md5(title + release_time + website_name)
                yield items
            meta_data = {'title': title, 'url': url, 'release_time': release_time, 'website_name': website_name}
            yield scrapy.Request(
                url,
                meta={'data': meta_data},
                callback=self.parse_detail,
                dont_filter=True,
                headers=self.headers
            )

    def parse_detail(self, response):
        data = response.meta['data']
        content = response.xpath(
            '//div[@class="content"]//p//text() | //div[@class="detail-news"]/font/text()').getall()
        content = ''.join(content)

        if not content:
            href = response.xpath('//div[@id="files"]/a/@href').get()
            attachment_url = response.urljoin(href)
            suffix = get_suffix(attachment_url)
            response = common_request(url=attachment_url, headers=self.headers, proxies_type=True)
            if 'pdf' in suffix:
                content = extract_pdf_text(response.content)
            elif 'xls' in suffix:
                content = extract_xlsx_text(response.content, input_format='xls', output_format='csv')
            elif 'docx' in suffix:
                content = extract_docx_text(response.content)
            content = '\n'.join(content)

        items = {}
        items['release_time'] = data['release_time']
        items['title'] = data['title']
        items['url'] = data['url']
        items['webname'] = data['website_name']
        items['content'] = content
        items['md5_value'] = hash_md5(data['title'] + data['release_time'] + data['website_name'])
        yield items

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
