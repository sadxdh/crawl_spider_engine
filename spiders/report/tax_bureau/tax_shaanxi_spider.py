"""陕西省税务局公告爬虫 → entity_government_announcement"""
import hashlib, scrapy; from lxml import etree; from spiders.base_spider import BaseSpider
_URL='https://shaanxi.chinatax.gov.cn'; _H={'User-Agent':'Mozilla/5.0'}

class ShaanxiTaxSpider(BaseSpider):
    name='report_tax_shaanxi'; data_table='entity_government_announcement'
    allowed_domains=['shaanxi.chinatax.gov.cn']
    custom_settings={'CONCURRENT_REQUESTS':8,'DOWNLOAD_DELAY':0.3}

    def start_requests(self):
        for page in range(self.start_page,self.end_page+1):
            yield scrapy.Request(_URL,headers=_H,callback=self.parse,
                errback=self.errback,meta={'page':page})

    def parse(self,response):
        try: tree=etree.HTML(response.body)
        except: return
        for li in tree.xpath('//ul[@class="list"]/li|//div[@class="list"]/ul/li'):
            t=li.xpath('./a/@title|./a/text()')
            h=li.xpath('./a/@href')
            d=li.xpath('./span/text()')
            if not t: continue
            title=t[0].strip(); date=d[0].strip() if d else ''
            url=response.urljoin(h[0]) if h else ''
            yield{'publish_time':date,'announcement_title':title,
                'announcement_url':url,'source':'陕西省税务局',
                'announcement_type':'',
                'abstract':'',
                'content':'',
                'emotion':'',
                'md5_value':hashlib.md5((date+title+'陕西省税务局').encode()).hexdigest(),
                '_table':'entity_government_announcement'}

    def errback(self,failure):self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
