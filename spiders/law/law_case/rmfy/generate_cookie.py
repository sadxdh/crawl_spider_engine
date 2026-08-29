import urllib.parse

from utils.decrypt import rmfy_encode_password
from utils.tools import *


class GenerateCookie():
    spider_name = "law_case_generate_cookie"

    def __init__(self):
        super(GenerateCookie, self).__init__()
        self.session = requests.Session()
        # self.session.proxies = switch_proxy(True, 'long_proxy')


    def get_login_url(self):
        headers = {
            'Host': 'rmfyalk.court.gov.cn',
            'Connection': 'keep-alive',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
            'Accept': '*/*',
            'sec-ch-ua': '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
            'Content-Type': 'application/json;charset=UTF-8',
            'Origin': 'https://rmfyalk.court.gov.cn',
            'Referer': 'https://rmfyalk.court.gov.cn/home.html?td=1',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        url = 'https://rmfyalk.court.gov.cn/cpws_al_api/api/user/getGdLoginUrl'
        response = self.session.post(
            url,
            headers=headers,
            json={},
            # method='post'
        )
        return response

    def parse_login_url(self, response):
        if response:
            try:
                response_data = response.json()
                login_url = response_data.get("data")
                # 从URL中提取state参数
                state_match = re.search(r'state=([^&]*)', login_url)
                signature_match = re.search(r'signature=([^&]*)', login_url)
                timestamp = re.search(r'timestamp=([^&]*)', login_url)
                state = state_match.group(1)
                state = urllib.parse.unquote(state)
                signature = signature_match.group(1)
                get_time = timestamp.group(1)
                return {'login_url': login_url, 'state': state, 'signature': signature, 'get_time': get_time}
            except Exception as e:
                logger.exception(f'{self.spider_name} 解析错误：{e}')

    def login(self, login_url, phone, password):
        headers = {
            "Host": "account.court.gov.cn",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Sec-Fetch-Dest": "document",
            "Referer": "https://rmfyalk.court.gov.cn/",
            "Accept-Encoding": "gzip, deflate, br, zstd",
        }
        redirect_response = self.session.get(login_url, headers=headers, allow_redirects=True)
        headers["Referer"] = redirect_response.url

        pwd = rmfy_encode_password(password)
        url = "https://account.court.gov.cn/api/login"
        data = {"username": phone, "password": pwd, "appDomain": "rmfyalk.court.gov.cn"}
        self.session.post(url, headers=headers, data=data)


    def authorize(self, login_url, signature, state, get_time):
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Referer": login_url,
            "Sec-Fetch-Dest": "document",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
            "sec-ch-ua": "\"Chromium\";v=\"142\", \"Microsoft Edge\";v=\"142\", \"Not_A Brand\";v=\"99\"",
        }
        params = {
            "signature": signature,
            "scope": "userinfo",
            "response_type": "code",
            "redirect_uri": "https://rmfyalk.court.gov.cn/",
            "state": state,
            "client_id": "CBS_FYALK_0",
            "timestamp": get_time
        }
        url = "https://account.court.gov.cn/oauth/authorize"
        response = self.session.get(url, headers=headers, params=params)
        try:
            get_id_url = response.url
            code = re.search(r'code=([^&]*)', response.url)
            code = code.group(1)
            return code, get_id_url
        except Exception as e:
            logger.exception(f'{self.spider_name} 解析错误: {e}')
            return None, None


    def loginGd(self, get_id_url, state, code):
        headers = {
            "Host": "rmfyalk.court.gov.cn",
            "Connection": "keep-alive",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
            "Accept": "*/*",
            "sec-ch-ua": "\"Chromium\";v=\"142\", \"Microsoft Edge\";v=\"142\", \"Not_A Brand\";v=\"99\"",
            "Content-Type": "application/json;charset=UTF-8",
            "sec-ch-ua-mobile": "?0",
            "Origin": "https://rmfyalk.court.gov.cn",
            "Referer": get_id_url,
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
        state = urllib.parse.unquote(state)  # 解码
        url = "https://rmfyalk.court.gov.cn/cpws_al_api/api/user/loginGd"
        data = {"code": code, "state": state, "mClient": ""}
        response = self.session.post(url, headers=headers, json=data)
        if response:
            cookies = response.cookies.get_dict()
            return cookies
        return None


    def main(self, phone, password):
        response = self.get_login_url()
        data = self.parse_login_url(response)
        if data:
            login_url = data.get("login_url")
            state = data.get("state")
            signature = data.get("signature")
            get_time = data.get("get_time")
            self.login(login_url, phone, password)
            code, get_id_url = self.authorize(login_url, signature, state, get_time)
            cookies = self.loginGd(get_id_url, state, code)
            return cookies
        return None
