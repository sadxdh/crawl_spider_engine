from scrapy import Request

from utils.time_kit import *
from utils.tools import *
from spiders.base_spider import BaseSpider
from utils.mysql_tools import select_data


class YunIosDetailSpider(BaseSpider):
    name = 'yun_company_app_ios_detail'
    data_table = 'app_info'
    custom_settings = {
        'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'middlewares.proxy_middleware.RandomProxyMiddleware': 510,
        }
    }
    proxy_type = 'long_proxy'

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,'
                  '*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cache-control': 'max-age=0',
        'priority': 'u=0, i',
    }

    def start_requests(self):
        num = int(self.end_page) - int(self.start_page)

        datas = select_data(
            table='app_info',
            data=['app_name', 'app_icon', 'tags', 'type', 'developer', 'operator', 'ios_url'],
            condition=f'ios_url is not null and ios_url != "" limit {num} offset {self.start_page}',
        )

        for data in datas:
            ios_url = data['ios_url']
            ios_url = ios_url.split('?')[0] + '?platform=iphone'

            yield Request(
                url=ios_url,
                headers=self.headers,
                meta={'data': data},
                callback=self.parse,
                dont_filter=True
            )

    def parse(self, response, **kwargs):
        meta = response.meta
        data = meta['data']
        app_name = data.get('app_name')

        app_icon_source = response.css('picture.we-artwork--ios-app-icon source[type="image/png"]::attr(srcset)').get()
        app_icon = app_icon_source.split('246w')[0] if app_icon_source else data['app_icon']

        abstract = response.xpath('//h2[contains(@class,"product-header__subtitle")]/text()').get()
        if abstract:
            abstract = abstract.strip()
        average_rating = response.xpath('//div[@class="we-customer-ratings__averages"]/span/text()').get()
        version = response.xpath('//p[contains(@class,"latest__version")]/text()').get()
        if version:
            version = version.split('版本')[-1]

        images = []
        rows = response.css('div.we-screenshot-viewer__screenshots ul li')
        for row in rows:
            source = row.css(
                'picture source[type="image/png"]::attr(srcset), picture source[type="image/jpeg"]::attr(srcset)'
            ).get()
            if source:
                image = source.split(',')[0].split(' ')[0]
                images.append(image)
        images = json.dumps(images)
        developer = response.xpath('//h2[contains(@class,"product-header__identity")]/a/text()').get()
        if developer:
            developer = developer.strip()
        summary = response.xpath('//div[@class="section__description"]//p/text()').getall()
        summary = '，'.join(summary)

        update_time = response.xpath('//*[@data-test-we-datetime]/text()').get()
        if update_time:
            update_time = dispose_update_date(update_time)
            if ',' in update_time:
                update_time = datetime.strptime(update_time, "%b %d, %Y").date()

        apk_size = response.xpath('//dt[contains(text(),"大小")]/following-sibling::dd/text()').get()
        try:
            log_text = response.xpath('//script[@id="shoebox-media-api-cache-apps"]/text()').get()
            log_json = json.loads(log_text)
            log_json = list(log_json.values())[0]
            rows = json.loads(log_json)['d']
            log_list = rows[0]['attributes']['platformAttributes']['ios']['versionHistory']
            log = json.dumps(log_list)
        except:
            log = None

        item = {}
        item['md5_value'] = hash_md5(f"{app_name}{developer}ios")
        item['app_name'] = app_name
        item['app_icon'] = app_icon
        item['developer'] = developer
        item['operator'] = data['operator']
        item['version'] = version
        item['update_date'] = update_time
        item['average_rating'] = average_rating
        item['apk_size'] = apk_size
        item['abstract'] = abstract
        item['summary'] = summary
        item['tags'] = data['tags']
        item['images'] = images
        item['type'] = data['type']
        item['log'] = log
        item['platform'] = 'ios'
        yield item
