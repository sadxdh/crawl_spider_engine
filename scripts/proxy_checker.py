#!/usr/bin/env python3
"""代理可用性定时检测 — 每 5 分钟校验代理服务，不可达时告警"""
import os, time, urllib.request, json
from datetime import datetime

CHECK_INTERVAL = int(os.environ.get('PROXY_CHECK_INTERVAL', '300'))
PROXY_SERVER = os.environ.get('SPIDER_PROXY_SERVER_PROD', '1wnv4qzl7pfzlk04xoo7.manage.wintaocloud.com')
PROXY_USER = os.environ.get('SPIDER_PROXY_USERNAME_PROD', '')
PROXY_PASS = os.environ.get('SPIDER_PROXY_PASSWORD_PROD', '')
DING_TOKEN = os.environ.get('DINGTALK_CRAWL_ERROR_TOKEN', '')

_last_state = None


def log(msg: str):
    print(f'[proxy_checker] {msg}', flush=True)


def send_alert(content: str):
    if not DING_TOKEN:
        return
    try:
        payload = json.dumps({
            'msgtype': 'text',
            'text': {'content': f'[代理检测] {content}'}
        }).encode()
        req = urllib.request.Request(DING_TOKEN, data=payload,
            headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def _extract_proxy(data: dict) -> str | None:
    proxy = data.get('proxy')
    if isinstance(proxy, dict):
        return proxy.get('http') or proxy.get('https')
    if isinstance(proxy, str) and proxy:
        return proxy
    return None


def test_proxy(timeout=10) -> tuple[bool, str]:
    """测试代理服务可达性，返回 (ok, msg)"""
    t0 = time.time()
    url = f'http://{PROXY_SERVER}/crawl-proxy-server/manage_proxy/get_dynamic_proxy'
    try:
        req = urllib.request.Request(url)
        if PROXY_USER:
            auth = f'{PROXY_USER}:{PROXY_PASS}'.encode()
            req.add_header('Proxy-Authorization', f'Basic {auth}')
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read())
        proxy = _extract_proxy(data)
        if proxy:
            return True, f'{proxy} (latency={(time.time()-t0):.1f}s)'
        return False, f'no proxy: {str(data)[:80]}'
    except Exception as e:
        return False, str(e)[:100]


def main():
    global _last_state
    log(f'启动, 检测间隔={CHECK_INTERVAL}s, 代理={PROXY_SERVER}')
    start = time.time()

    while True:
        time.sleep(CHECK_INTERVAL)
        ok, msg = test_proxy()
        now = datetime.now().strftime('%H:%M:%S')

        if ok:
            if _last_state is False:
                log(f'{now} 代理已恢复: {msg}')
                send_alert(f'代理已恢复 {now}\n{msg}')
            else:
                log(f'{now} {msg}')
            _last_state = True
        else:
            if _last_state is not False:
                log(f'{now} 代理不可达: {msg}')
                send_alert(f'代理不可达 {now}\n服务器: {PROXY_SERVER}\n错误: {msg}')
            else:
                log(f'{now} 代理仍不可达: {msg}')
            _last_state = False


if __name__ == '__main__':
    main()
