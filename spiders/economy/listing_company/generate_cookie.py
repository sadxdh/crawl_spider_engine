import json
from utils.tools import *



class GenerateCookie():
    def __init__(self):
        super().__init__()
        self.headers = {
            "accept": "application/json",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "app-device": "WEB",
            "content-type": "application/json",
            "origin": "https://www.riskbird.com",
            "referer": "https://www.riskbird.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
        }

    def login(self, phone, password):
        url = "https://www.riskbird.com/api/auth/login"
        data = {
            "mobile": phone,
            "captcha": "",
            "smsCode": "",
            "password": password,
            "inviteCode": None,
            "type": "password"
        }
        data = json.dumps(data, separators=(',', ':'))
        response = common_request(url, headers=self.headers, data=data, method='post', proxies_type=False)
        if response:
            cookies = response.cookies.get_dict()
            return cookies
        return None
