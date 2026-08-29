"""
加速乐 (JSL) 521 绕过工具
移植自 yuncrawl/crawl/utils/decrypt_jsl.py
"""
import re, json, hashlib
from py_mini_racer import MiniRacer


def _exec_js(code: str) -> str:
    """使用 PyMiniRacer 执行 JS 代码"""
    ctx = MiniRacer()
    ctx.eval('var location = {href: "https://www.example.com/"}')
    ctx.eval('var navigator = {userAgent: "Mozilla/5.0"}')
    ctx.eval('var window = globalThis')
    ctx.eval('var document = {cookie: ""}')
    try:
        result = ctx.eval(code)
        return str(result) if result else ''
    except Exception:
        return ''


def encrypt_ck_1(response_text: str) -> dict:
    """第一轮 JSL challenge — 提取简单算术 cookie"""
    code = re.findall(r"cookie=(.*?)\+\(';'\)", response_text, re.S)
    code = ''.join(code)
    if not code:
        # 新格式: document.cookie=('_')+('_')+...
        match = re.search(r"document\.cookie=\((.*?)\)\+", response_text)
        if match:
            # 提取整个表达式并执行
            full_match = re.search(r"document\.cookie=((?:'[^']*'|\([^)]*\)|\+)+)", response_text)
            if full_match:
                code = 'var __ck = ' + full_match.group(1) + '; __ck'
    if not code:
        return {}
    ck_val = _exec_js(code)
    if '=' in ck_val:
        name, value = ck_val.split('=', 1)
        value = value.split(';')[0]
        return {name.strip(): value.strip()}
    return {}


def encrypt_ck_2(response_text: str, cookie_name: str = '__jsl_clearance_s') -> dict:
    """第二轮 JSL challenge — 破解 go() 函数"""
    result = response_text if isinstance(response_text, str) else response_text
    # 匹配 go({...})
    match = re.findall(r';go\((.*?)\)</script>', result)
    if not match:
        return {}
    try:
        data = json.loads(match[0])
    except json.JSONDecodeError:
        return {}

    if 'chars' not in data or 'bts' not in data or 'ha' not in data or 'ct' not in data:
        return {}

    for i in data['chars']:
        for j in data['chars']:
            vales = data['bts'][0] + i + j + data['bts'][1]
            if data['ha'] == 'sha256':
                if data['ct'] == hashlib.sha256(vales.encode()).hexdigest():
                    return {cookie_name: vales}
            elif data['ha'] == 'md5':
                if data['ct'] == hashlib.md5(vales.encode()).hexdigest():
                    return {cookie_name: vales}
            elif data['ha'] == 'sha1':
                if data['ct'] == hashlib.sha1(vales.encode()).hexdigest():
                    return {cookie_name: vales}
    return {}


def solve_jsl(session, url: str, headers: dict = None) -> bool:
    """完整的 JSL 521 绕过流程，直接在 session 上设置 cookie"""
    from curl_cffi import requests as cr
    h = headers or {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36'}
    impersonate = 'chrome124'

    # 第一轮
    r1 = session.get(url, headers=h, impersonate=impersonate, timeout=15)
    if r1.status_code != 521:
        return r1.status_code == 200

    ck1 = encrypt_ck_1(r1.text)
    if ck1:
        for k, v in ck1.items():
            session.cookies.set(k, v)

    # 第二轮
    r2 = session.get(url, headers=h, impersonate=impersonate, timeout=15)
    ck2 = encrypt_ck_2(r2.text, '__jsl_clearance_s')
    if ck2:
        for k, v in ck2.items():
            session.cookies.set(k, v)

    return bool(ck1 or ck2)
