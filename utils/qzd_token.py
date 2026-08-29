"""
企知道 (qizhidao.com) Token 管理器
参照旧项目: data_crawl_server invoice_title/account_login.py
"""
import base64, hashlib, json, time, requests
from Crypto.Cipher import AES as _AES
from loguru import logger

_LOGIN_URL = 'https://ips-sso.qizhidao.com/v1/security/login_password'
_ADMIN_URL = 'https://app.qizhidao.com/qzd-bff-app/qzd/sso/adminLogin'
_CLIENT_ID = '9304622189680257'
_AES_KEY = '46cc793c53dc451b'
_COMPANY_ID = 'B955031393495367680'

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


def encrypt_password(password: str) -> str:
    """AES-ECB 加密密码"""
    from Crypto.Util.Padding import pad
    key_bytes = _AES_KEY.encode('utf-8')
    data_bytes = password.encode('utf-8')
    padded = pad(data_bytes, _AES.block_size)
    cipher = _AES.new(key_bytes, _AES.MODE_ECB)
    return base64.b64encode(cipher.encrypt(padded)).decode('utf-8')


def get_qzd_signature(data: dict, call_func: str = 'get_signature_40') -> str:
    """通过 node_service 生成企知道签名"""
    try:
        import subprocess, os
        js_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'qzd_sign.js')
        data_json = json.dumps(data, ensure_ascii=False)
        # 通过 node 执行
        code = f'const {{ {call_func} }} = require("{js_path.replace(chr(92), "/")}"); console.log({call_func}({data_json}));'
        result = subprocess.run(['node', '-e', code], capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        logger.warning(f'qzd signature failed: {result.stderr[:200]}')
    except FileNotFoundError:
        logger.warning('node not available')
    except Exception as e:
        logger.warning(f'qzd signature error: {e}')
    return ''


def login_qzd(phone: str, password: str) -> str:
    """登录企知道，返回 token"""
    # Step 1: 密码登录获取 ticket
    enc_pwd = encrypt_password(password)
    body = {'clientId': _CLIENT_ID, 'username': phone, 'password': enc_pwd}
    try:
        resp = requests.post(_LOGIN_URL, json=body, headers=_HEADERS, timeout=15)
        data = resp.json()
        ticket = data.get('data', {}).get('ticket', '')
        if not ticket:
            logger.warning(f'qzd login failed: {resp.text[:200]}')
            return ''
    except Exception as e:
        logger.error(f'qzd login error: {e}')
        return ''

    # Step 2: 二次验证登录
    admin_data = {
        'companyId': _COMPANY_ID,
        'time': int(time.time()),
        'ticket': ticket,
        'platformType': '3',
    }
    signature = get_qzd_signature(admin_data, 'get_signature_40')
    hdrs = dict(_HEADERS)
    hdrs['signature'] = signature
    try:
        resp2 = requests.post(_ADMIN_URL, json=admin_data, headers=hdrs, timeout=15)
        result = resp2.json()
        if result.get('success'):
            logger.info(f'qzd login success: {phone}')
            return ticket
        logger.warning(f'qzd admin login failed: {resp2.text[:200]}')
    except Exception as e:
        logger.error(f'qzd admin login error: {e}')
    return ''
