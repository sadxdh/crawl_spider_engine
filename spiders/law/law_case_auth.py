"""人民法院案例库 OAuth 登录 → 获取 cookies
迁移自: data_crawl_server law_case/rmfy/generate_cookie.py
流程: getGdLoginUrl → 密码登录(RSA) → OAuth授权 → loginGd → cookies
"""
import base64, json, random, re, urllib.parse
import requests
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from loguru import logger

_PUBLIC_KEY = (
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA5GVku07yXCndaMS1evPIPyWwhbdWMVRqL4qg4OsKbzyTGmV4YkG8H0hwwrFLuPhqC5tL136aaizuL/lN5DRRbePct6syILOLLCBJ5J5rQyGr00l1zQvdNKYp4tT5EFlqw8tlPkibcsd5Ecc8sTYa77HxNeIa6DRuObC5H9t85ALJyDVZC3Y4ES/u61Q7LDnB3kG9MnXJsJiQxm1pLkE7Zfxy29d5JaXbbfwhCDSjE4+dUQoq2MVIt2qVjZSo5Hd/bAFGU1Lmc7GkFeLiLjNTOfECF52ms/dks92Wx/glfRuK4h/fcxtGB4Q2VXu5k68e/2uojs6jnFsMKVe+FVUDkQIDAQAB"
)


def _encrypt_password(password: str) -> str:
    """RSA 加密密码 (参照 rmfy_encode_password)"""
    rsa_key = RSA.import_key(f"-----BEGIN PUBLIC KEY-----\n{_PUBLIC_KEY}\n-----END PUBLIC KEY-----")
    cipher = PKCS1_v1_5.new(rsa_key)
    encrypted = cipher.encrypt(password.encode())
    return urllib.parse.quote(base64.b64encode(encrypted).decode())


def generate_cookie(phone: str, password: str) -> dict | None:
    """执行完整 OAuth 登录流程，返回 cookies dict"""
    session = requests.Session()

    # Step 1: 获取 OAuth 登录 URL
    h = {
        'Host': 'rmfyalk.court.gov.cn',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://rmfyalk.court.gov.cn',
        'Referer': 'https://rmfyalk.court.gov.cn/home.html?td=1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142.0.0.0 Safari/537.36',
    }
    try:
        r = session.post(
            'https://rmfyalk.court.gov.cn/cpws_al_api/api/user/getGdLoginUrl',
            headers=h, json={}, timeout=30,
        )
        login_url = r.json().get('data', '')
        if not login_url:
            logger.warning('law_case: getGdLoginUrl 返回空')
            return None
    except Exception as e:
        logger.warning(f'law_case: getGdLoginUrl 失败: {e}')
        return None

    # 提取 URL 参数
    state_m = re.search(r'state=([^&]*)', login_url)
    sig_m = re.search(r'signature=([^&]*)', login_url)
    ts_m = re.search(r'timestamp=([^&]*)', login_url)
    if not state_m or not sig_m:
        logger.warning('law_case: 无法解析 login URL 参数')
        return None
    state = urllib.parse.unquote(state_m.group(1))
    signature = sig_m.group(1)
    get_time = ts_m.group(1) if ts_m else ''

    # Step 2: 密码登录 account.court.gov.cn
    h2 = {
        'Host': 'account.court.gov.cn',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://rmfyalk.court.gov.cn/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142.0.0.0 Safari/537.36',
    }
    try:
        session.get(login_url, headers=h2, allow_redirects=True, timeout=30)
        enc_pwd = _encrypt_password(password)
        session.post(
            'https://account.court.gov.cn/api/login',
            headers=h2,
            data={'username': phone, 'password': enc_pwd, 'appDomain': 'rmfyalk.court.gov.cn'},
            timeout=30,
        )
    except Exception as e:
        logger.warning(f'law_case: 登录失败: {e}')
        return None

    # Step 3: OAuth 授权获取 code
    h3 = {
        'Accept': 'text/html,application/xhtml+xml,*/*',
        'Referer': login_url,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142.0.0.0 Safari/537.36',
    }
    try:
        r = session.get(
            'https://account.court.gov.cn/oauth/authorize',
            headers=h3,
            params={
                'signature': signature, 'scope': 'userinfo', 'response_type': 'code',
                'redirect_uri': 'https://rmfyalk.court.gov.cn/', 'state': state,
                'client_id': 'CBS_FYALK_0', 'timestamp': get_time,
            },
            timeout=30,
        )
        code_m = re.search(r'code=([^&]*)', r.url)
        if not code_m:
            logger.warning(f'law_case: 无法获取 OAuth code, url={r.url[:200]}')
            return None
        code = code_m.group(1)
        get_id_url = r.url
    except Exception as e:
        logger.warning(f'law_case: OAuth授权失败: {e}')
        return None

    # Step 4: 交换 cookies
    h4 = {
        'Host': 'rmfyalk.court.gov.cn',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://rmfyalk.court.gov.cn',
        'Referer': get_id_url,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142.0.0.0 Safari/537.36',
    }
    try:
        r = session.post(
            'https://rmfyalk.court.gov.cn/cpws_al_api/api/user/loginGd',
            headers=h4,
            json={'code': code, 'state': urllib.parse.unquote(state), 'mClient': ''},
            timeout=30,
        )
        cookies = r.cookies.get_dict()
        if cookies:
            logger.info(f'law_case: cookie 获取成功 ({phone})')
            return cookies
        logger.warning(f'law_case: cookie 为空')
    except Exception as e:
        logger.warning(f'law_case: loginGd 失败: {e}')
    return None
