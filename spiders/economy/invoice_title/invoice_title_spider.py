"""发票抬头 → invoice_title
参照旧项目: data_crawl_server invoice_title/qzd_spider.py
API: app.qizhidao.com
"""
import hashlib, json, scrapy
from spiders.base_spider import BaseSpider
from utils.admin_account_client import account_client
from utils.account_service import account_service
from utils.qzd_token import login_qzd

_HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh-CN,zh;q=0.9',
    'content-type': 'application/json',
    'device-id': 'BUcYQelcXS14I1H+d4dYQ4Am8iSKG5a63T50diuK+erjBC4MSk5wBUhICeBNI5ofCA1OKIHLCd/FKl4aSQaxNkA==',
    'h5version': 'v1.0.0',
    'origin': 'https://www.qizhidao.com',
    'referer': 'https://www.qizhidao.com/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/134.0.0.0 Safari/537.36',
    'user-agent-web': 'X/8fbaaa7b8c72482229d72c9a3e569255',
}


class InvoiceTitleSpider(BaseSpider):
    name = 'economy_invoice_title'
    data_table = 'invoice_title'
    dedup_fields = ['md5_value']
    allowed_domains = ['app.qizhidao.com', 'www.qizhidao.com', 'ips-sso.qizhidao.com']
    default_end_page = 1
    proxy_type = 'no_proxy'  # 登录类爬虫不使用代理

    custom_settings = {'CONCURRENT_REQUESTS': 2, 'DOWNLOAD_DELAY': 1, 'COOKIES_ENABLED': True}

    def start_requests(self):
        # 从平台/Redis获取企知道账号并登录
        accounts = account_client.get_accounts('invoice_title')
        if not accounts:
            # 兜底：从本地Redis获取
            acc_data = account_service.get_accounts('invoice_title')
            if acc_data:
                accounts = [{'phone': k, 'password': v} for k, v in acc_data.items()]
        if not accounts:
            self.log_warning('无可用企知道账号')
            return
        acc = accounts[0]
        phone = acc.get('phone', '')
        password = acc.get('password', '')
        if not phone or not password:
            self.log_warning('账号缺少phone或password')
            return

        token = login_qzd(phone, password)
        if not token:
            self.log_warning(f'企知道登录失败: {phone}')
            return

        self.log_info(f'企知道登录成功: {phone}')
        self._token = token
        hdrs = dict(_HEADERS)
        hdrs['accesstoken'] = token
        hdrs['token'] = token
        # 生成签名
        from utils.qzd_token import get_qzd_signature
        signature = get_qzd_signature(token, 'get_signature_39')
        hdrs['signature'] = signature
        self._headers = hdrs

        # 搜索公司获取发票抬头
        for keyword in ['阿里巴巴', '腾讯', '华为', '百度', '京东', '字节跳动', '美团', '网易']:
            body = json.dumps({'category_new': [], 'prefix': keyword, 'size': 3, 'status': '', 'type': 0})
            yield scrapy.Request(
                url='https://app.qizhidao.com/qzd-bff-pcweb/qzd/v1/search/enterprisea/suggestPredict',
                method='POST', headers=hdrs, body=body,
                callback=self._parse_search, errback=self.errback)

    def _parse_search(self, response):
        try:
            data = response.json()
            results = data.get('data', {}).get('querys', [])
        except Exception:
            return
        for r in results:
            eid = r.get('eid', '')
            if not eid:
                continue
            body = json.dumps({'eid': eid})
            yield scrapy.Request(
                url='https://app.qizhidao.com/qzd-bff-enterprise/qzd/v1/pc/invoice/queryInvoiceTitle',
                method='POST', headers=self._headers, body=body,
                callback=self._parse_invoice, errback=self.errback)

    def _parse_invoice(self, response):
        try:
            data = response.json().get('data', {})
        except Exception:
            return
        if not data:
            return
        company_name = data.get('company_name', '')
        if not company_name:
            return
        yield {
            'company_name': company_name,
            'tax_code': data.get('tax_code', ''),
            'bank_name': data.get('bank_name', ''),
            'bank_account': data.get('bank_account', ''),
            'address': data.get('address', ''),
            'phone': data.get('phone', ''),
            'logo': data.get('logo', ''),
            'md5_value': hashlib.md5((company_name + str(data.get('tax_code', ''))).encode()).hexdigest(),
        }

    def errback(self, failure):
        self.log_error(f'请求失败: {failure.request.url} — {failure.value}')
