import urllib.parse
import requests

from utils.decrypt import rmfy_encode_password
from utils.tools import *


class GenerateCookie():
    spider_name = "law_case_dy_generate_cookie"

    def __init__(self):
        super(GenerateCookie, self).__init__()
        self.session = requests.Session()
        # self.session.proxies = switch_proxy(True, 'long_proxy')

    def authorize(self):
        # 1
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Connection': 'keep-alive',
            'Referer': 'https://dyjfalk.court.gov.cn/login?source=tyzhzx',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0',
        }

        url = "https://dyjfalk.court.gov.cn/dyjfAlkInternet-admin/tyzhzx/authorize"
        response = self.session.get(url=url, headers=headers)
        authorize_url = response.json()['data']
        return authorize_url

    def get_back_url(self, authorize_url):
        # 2
        headers_2 = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Referer': 'https://dyjfalk.court.gov.cn/',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0',
        }
        response = self.session.get(url=authorize_url, headers=headers_2)
        back_url = response.url
        back_url = back_url.split('#')[0]
        return back_url

    def login(self, phone, password, back_url):
        # 3
        headers_3 = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://account.court.gov.cn',
            'Pragma': 'no-cache',
            'Referer': back_url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0',
            'X-Requested-With': 'XMLHttpRequest',
        }
        url = 'https://account.court.gov.cn/api/login'
        data = {
            'username': phone,
            'password': rmfy_encode_password(password),
            'appDomain': 'dyjfalk.court.gov.cn',
        }
        self.session.post(url=url, headers=headers_3, data=data)

    def get_code_url(self, back_url, authorize_url):
        # 4
        headers_4 = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Referer': back_url,
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0',
        }

        response = self.session.get(url=authorize_url, headers=headers_4)
        logging_url = response.url
        logging_in_url = urllib.parse.unquote(logging_url)
        code_url = re.search(r'redirect_uri=(.*)', logging_in_url).group(1)
        return code_url, logging_url

    def get_cookie(self, code_url, logging_url):
        # 5
        headers_5 = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Referer': logging_url,
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0',
        }

        response = self.session.get(url=code_url, headers=headers_5, allow_redirects=False)
        if response:
            cookies = response.cookies.get_dict()
            return cookies
        return None

    def main(self, phone, password):
        authorize_url = self.authorize()
        back_url = self.get_back_url(authorize_url)
        self.login(phone, password, back_url)
        code_url, logging_url = self.get_code_url(back_url, authorize_url)
        cookies = self.get_cookie(code_url, logging_url)
        return cookies
