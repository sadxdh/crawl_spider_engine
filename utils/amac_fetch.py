"""AMAC API 请求工具 — 使用 requests 直接请求绕过 Twisted TLS 指纹问题"""
import requests as req
from scrapy.http import HtmlResponse


def amac_post(url, body='{}', timeout=30):
    """POST 请求 AMAC API, 返回 Scrapy HtmlResponse"""
    headers = {
        'Content-Type': 'application/json',
        'Host': 'gs.amac.org.cn',
        'Referer': 'https://gs.amac.org.cn/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
    }
    try:
        r = req.post(url, headers=headers, data=body, timeout=timeout)
        r.encoding = r.apparent_encoding or 'utf-8'
        resp = HtmlResponse(url=str(r.url), status=r.status_code, body=r.content, encoding=r.encoding or 'utf-8')
        resp.status_code = r.status_code
        return resp
    except Exception:
        return None


def amac_get(url, timeout=30):
    """GET 请求 AMAC 页面"""
    headers = {
        'Host': 'gs.amac.org.cn',
        'Referer': 'https://gs.amac.org.cn/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
    }
    try:
        r = req.get(url, headers=headers, timeout=timeout)
        r.encoding = r.apparent_encoding or 'utf-8'
        resp = HtmlResponse(url=str(r.url), status=r.status_code, body=r.content, encoding=r.encoding or 'utf-8')
        resp.status_code = r.status_code
        return resp
    except Exception:
        return None
