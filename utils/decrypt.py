import base64
import math
import os
import hashlib
import time
import urllib.parse
import execjs
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad
CUR_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_PATH = os.path.join(CUR_DIR, '../static')


def zn_group_aes_encrypt():
    # 密钥
    key = b'1234567887654321'
    # 初始化向量(可选)
    iv = b'1234567887654321'
    # 明文
    plaintext = bytes(str(math.floor(time.time())), encoding='utf-8')

    # 创建 AES-128-CBC 加密器
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_plaintext = pad(plaintext, AES.block_size)
    # 加密明文
    encrypted = cipher.encrypt(padded_plaintext)

    return base64.b64encode(encrypted).decode('utf-8')


def get_uuid():
    exec_path = os.path.join(STATIC_PATH, 'moj_gov.js')
    with open(exec_path, 'r') as f:
        js_code = f.read()

    execute = execjs.compile(js_code)
    r = execute.call('generate_uuid')
    return r


def generate_number(v_key, guid, page_num, page_size=12):
    # 计算 MD5
    str_to_hash = v_key + guid + str(page_num) + "." + str(page_size)
    encoded_str = urllib.parse.quote(str_to_hash)
    md5_str = hashlib.md5(encoded_str.encode()).hexdigest()

    # 计算特定位置字符的 ASCII 码并求和
    number = (
            ord(md5_str[10]) +
            ord(md5_str[3]) +
            ord(md5_str[1]) +
            ord(md5_str[6]) +
            ord(md5_str[8]) +
            ord(md5_str[5])
    )
    return number


def decrypt_jilin_spider(data, call_func="decode"):
    exec_path = os.path.join(STATIC_PATH, 'product_recall_jilin_spider.js')
    with open(exec_path, 'r', encoding='utf-8') as f:
        js_code = f.read()
    execute = execjs.compile(js_code)
    r = execute.call(call_func, data)
    return r


def decrypt_sign_qzd_spider(data, call_func="get_signature_39"):
    exec_path = os.path.join(STATIC_PATH, 'qzd_sign.js')
    with open(exec_path, 'r', encoding='utf-8') as f:
        js_code = f.read()
    execute = execjs.compile(js_code)
    r = execute.call(call_func, data)
    return r


def decrypt_title_transaction_spider(phone, time_stamp, user_info):
    exec_path = os.path.join(STATIC_PATH, 'title_transaction.js')
    with open(exec_path, 'r', encoding='utf-8') as f:
        js_code = f.read()
    execute = execjs.compile(js_code)
    r = execute.call('generate_cookie', phone, time_stamp, user_info)
    return r


def decrypt_diandian_data_spider(e, path, n, r):
    exec_path = os.path.join(STATIC_PATH, 'diandian_data.js')
    with open(exec_path, 'r', encoding='utf-8') as f:
        js_code = f.read()
    execute = execjs.compile(js_code)
    r = execute.call('params_k', e, path, n, r)
    return r


# 人民法院-多元解纷
def rmfy_encode_password(password):
    public_key = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA5GVku07yXCndaMS1evPIPyWwhbdWMVRqL4qg4OsKbzyTGmV4YkG8H0hwwrFLuPhqC5tL136aaizuL/lN5DRRbePct6syILOLLCBJ5J5rQyGr00l1zQvdNKYp4tT5EFlqw8tlPkibcsd5Ecc8sTYa77HxNeIa6DRuObC5H9t85ALJyDVZC3Y4ES/u61Q7LDnB3kG9MnXJsJiQxm1pLkE7Zfxy29d5JaXbbfwhCDSjE4+dUQoq2MVIt2qVjZSo5Hd/bAFGU1Lmc7GkFeLiLjNTOfECF52ms/dks92Wx/glfRuK4h/fcxtGB4Q2VXu5k68e/2uojs6jnFsMKVe+FVUDkQIDAQAB"
    # 导入公钥
    rsa_key = RSA.import_key(f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----")
    # 创建加密器
    cipher = PKCS1_v1_5.new(rsa_key)
    # 加密数据
    encrypted = cipher.encrypt(password.encode())
    # Base64编码并URL编码
    encoded = base64.b64encode(encrypted).decode()
    return urllib.parse.quote(encoded)
