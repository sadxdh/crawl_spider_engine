import os
import random
import string
import time

import execjs
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes
import base64
from utils.proxy_kit import ScrapyProxy
from loguru import logger

CUR_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_PATH = os.path.join(CUR_DIR, '../../static')

def _0x2bd810(x):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(x))


def _0x41147e(x, _):
    # Convert input strings to bytes
    n = x.encode('utf-8')
    d = _0x2bd810(16)  # Generate random 16-character string
    f = d.encode('utf-8')
    b = _.encode('utf-8')
    # Pad the plaintext to be multiple of AES block size (16 bytes)
    b = pad(b, AES.block_size)
    # Generate the cipher using CBC mode
    iv = get_random_bytes(AES.block_size)
    cipher = AES.new(f, AES.MODE_CBC, iv)
    t = cipher.encrypt(b)
    r = iv + t
    return base64.b64encode(r).decode('utf-8')

def get_MM_mq4qQammP3BA4(MM_mq4qQammP3BA4, kks):
    exec_path = os.path.join(STATIC_PATH, 'hunan_chinatax.js')
    with open(exec_path, "r") as file:
        js_code = file.read()

    MM_1xL8nvQydGCE4 = execjs.compile(js_code).call("_0x41147e", MM_mq4qQammP3BA4, kks)
    return MM_1xL8nvQydGCE4


def fake_rs_request(url, headers):
    try:
        proxy = ScrapyProxy.get_long_proxy()
        proxies = {
            "http": proxy,
            "https": proxy,
        }
        cookie = requests.get(url=url, headers=headers, proxies=proxies).cookies
        MM_mq4qQammP3BA4 = cookie['MM_mq4qQammP3BA4'][:32]
        kks = f"ts={int(time.time() * 1000)}&fp=3dd604a0aba2790104c899f9306b1630&device=PC&engine=Blink&version=135.0.0.0&browser=Chrome&os=Windows 10&botd=-1"
        MM_1xL8nvQydGCE4 = get_MM_mq4qQammP3BA4(MM_mq4qQammP3BA4, kks)
        cookie['MM_1xL8nvQydGCE4'] = MM_1xL8nvQydGCE4
        response = requests.get(url=url, cookies=cookie, headers=headers, proxies=proxies)
        return response
    except Exception as e:
        logger.error(e)
        return None


# headers = {
#         "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
#         "accept-language": "zh-CN,zh;q=0.9",
#         "cache-control": "max-age=0",
#         "priority": "u=0, i",
#         # "referer": "https://hunan.chinatax.gov.cn/lists/20190409002106/1",
#         "sec-ch-ua": "\"Google Chrome\";v=\"137\", \"Chromium\";v=\"137\", \"Not/A)Brand\";v=\"24\"",
#         "sec-ch-ua-mobile": "?0",
#         "sec-ch-ua-platform": "\"Windows\"",
#         "sec-fetch-dest": "document",
#         "sec-fetch-mode": "navigate",
#         "sec-fetch-site": "same-origin",
#         "sec-fetch-user": "?1",
#         "upgrade-insecure-requests": "1",
#         "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
#     }
# print(fake_rs_request(url='https://hunan.chinatax.gov.cn/lists/20190409002106/1', headers=headers).text)






