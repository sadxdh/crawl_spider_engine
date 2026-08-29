import re
import json
import base64
import random
from hashlib import md5
from lxml import etree, html
from urllib.parse import urlparse
import execjs
try: import ddddocr
except ImportError: ddddocr = None
try: from opencc import OpenCC
except ImportError: OpenCC = None
try: from playwright.sync_api import sync_playwright
except ImportError: sync_playwright = None
try: from selenium import webdriver
except ImportError: webdriver = None
from bs4 import BeautifulSoup, Comment
from html import unescape
from lxml import etree, html
from urllib.parse import urljoin
from utils.proxy_kit import ScrapyProxy
import requests
from loguru import logger
import hashlib
import time


def serialize(data: dict) -> str:
    """序列化数据为JSON字符串"""
    return json.dumps(data)

def deserialize(data: str) -> dict:
    """反序列化JSON字符串为字典"""
    return json.loads(data) if data else {}


def hash_md5(str_content):
    m5 = md5()
    m5.update(str_content.encode('utf8'))
    content_md5 = m5.hexdigest()
    return content_md5


def captcha_parse(content):
    # 文字验证码识别
    ocr = ddddocr.DdddOcr(show_ad=False, det=False)
    ocr_res = ocr.classification(content)
    return ocr_res


def slider_validation_captcha(bg, tr):
    # 滑块验证码距离识别
    det_ocr = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)

    with open(bg, 'rb') as f:
        target_bytes = f.read()

    with open(tr, 'rb') as f:
        background_bytes = f.read()

    ocr_res = det_ocr.slide_match(background_bytes, target_bytes)
    return ocr_res


def get_offset():
    """ 获取缺口偏移量 """
    ocr_res = slider_validation_captcha(bg='bigImg.jpg', tr='tarImg.jpg')
    offset = ocr_res.get('target')[0]
    i = 250 * offset / 280
    offset = offset + (i - i // 1)
    return offset


def create_selenium_browser():
    """远程selenium渲染"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    browser = webdriver.Chrome(options=options)
    browser.set_page_load_timeout(30)
    browser.implicitly_wait(30)
    return browser


def selenium_request(browser, url):
    browser.get(url)
    response = browser.page_source
    return response


def create_playwright_browser(**kwargs):
    """playwright创建浏览器"""
    driver = sync_playwright().start()
    browser = driver.chromium.launch(**kwargs)
    return browser


def playwright_request(browser, url, cookie=None, headers=None, proxy=None):
    """上下文创建请求"""
    context = browser.new_context(proxy=proxy)
    try:
        if cookie:
            context.add_cookies(cookies=cookie)
        page = context.new_page()
        try:
            if headers:
                page.set_extra_http_headers(headers)
            page.goto(url, timeout=600000)
            cookies = context.cookies()
            content = page.content()
            return content, cookies
        finally:
            # 确保page被关闭
            page.close()
    finally:
        # 确保context被关闭
        context.close()


def match_text(text, pattern=r'(\d{4}-\d{2}-\d{2})', placeholder=''):
    """
    正则匹配
    @param text:
    @param pattern: 正则表达式 默认匹配日期
    @param placeholder: 占位符默认为空
    """
    if text:
        result = re.findall(pattern, text)
        tuple_list = [i for item in result if isinstance(item, tuple) for i in item]
        match = [i for i in result if isinstance(i, str)]
        match.extend(tuple_list)
        result = placeholder.join(match) if match else None
        return result
    return None


def xpath_parse(
        response: etree._Element,
        xpath_content: str,
        placeholder='',
        return_list=False,
        ):
    """
    xpath 解析
    :param response: etree._Element
    :param xpath_content: xpath content
    :param placeholder: 占位符默认为空
    :param return_list: 默认为False true返回解析列表，False获取列表中的值
    """
    result = response.xpath(xpath_content)
    if not result:
        return [] if return_list else None
    else:
        if isinstance(result[0], etree._Element):
            return result if return_list else result[0]
        else:
            return result if return_list else placeholder.join(result).strip().replace('\xa0', '')


def html_del_attr_tag(content: html.HtmlElement, del_tag=None, del_attr=None):
    del_tag = del_tag if del_tag else []
    del_attr = del_attr if del_attr else []

    # 删除标签
    for xpath in del_tag:
        elems = content.xpath(xpath)
        for elem in elems:
            parent = elem.getparent()
            parent.remove(elem)

    # 删除style属性
    for xpath in del_attr:
        elems = content.xpath(xpath)
        for elem in elems:
            elem.attrib.pop('style')

    return content


def chinese_traditional_to_simplified(text):
    """
    香港繁体转简体
    :params text: 香港字体文本
    """
    cc = OpenCC('hk2s')
    result = cc.convert(text)
    return result


def extract_domain_protocol(url):
    """提取url中的域名和协议"""
    parsed_url = urlparse(url)
    return f"{parsed_url.scheme}://{parsed_url.netloc}"


def html_to_str(html_content, xpath_content):
    html_text = html.fromstring(html_content)
    content = xpath_parse(html_text, xpath_content)
    content = html.tostring(content, encoding='unicode')
    return content


def exec_js(js_code):
    """node执行js代码"""
    execute = execjs.compile(js_code)
    r = execute.eval(js_code)
    return r


def exec_js_param(js_code, call_func, *args):
    """执行带参数的js
    :param js_code: js代码
    :param call_func: 被调用的方法
    :param args: 方法需传入的参数
    """
    execute = execjs.compile(js_code)
    r = execute.call(call_func, *args)
    return r


def cookie_to_cookieJar(cookies: dict, domain: str, path: str = "/"):
    """
    将字典格式的 cookies 转换为 Playwright 兼容的 Cookie Jar 列表格式。

    :param cookies: 字典格式的 cookies，如 {"name1": "value1", ...}
    :param domain: Cookie 的域名
    :param path: Cookie 的路径，默认为 /
    :return: Playwright 兼容的 Cookie 列表
    """
    if not cookies:
        return []

    cookie_jar = []
    for name, value in cookies.items():
        cookie_jar.append({
            "name": name,
            "value": value,
            "domain": domain,
            "path": path
        })

    return cookie_jar


def base64_to_binary(base64_str):
    # base64格式转二进制
    if "base64," in base64_str:
        base64_str = base64_str.split("base64,")[1]
    binary_data = base64.b64decode(base64_str)
    return binary_data

def get_node_html(response,
                  content_xpath: str,
                  clear_font_style: bool = False,
                  rm_node_xpath: list = None,
                  rm_href_xpath: str = None,
                  replace_href_xpath: str = None,
                  replace_node_xpath: str = None,
                  replace_src_xpath: str = None):
    """
    获取节点 html 代码
    :param response: 支持 requests.Response / scrapy.Response / playwright APIResponse / html字符串
    :param content_xpath: 内容 xpath
    :param clear_font_style: 清除 style 里的 font-family
    :param rm_node_xpath: 删除指定节点，传 list
    :param rm_href_xpath: 删除 href 属性
    :param replace_href_xpath: 把 href 补成绝对链接
    :param replace_node_xpath: 替换整个节点
    :param replace_src_xpath: 把 src 补成绝对链接
    :return: html 字符串
    """
    url = ""

    if isinstance(response, requests.models.Response):
        url = response.url
        response_text = response.text

    elif hasattr(response, "text") and hasattr(response, "url"):
        # 兼容 scrapy Response / HtmlResponse
        url = response.url
        response_text = response.text

    elif hasattr(response, "body") and callable(response.body) and hasattr(response, "url"):
        # 兼容 playwright APIResponse
        url = response.url
        response_text = response.body().decode("utf-8", errors="ignore")

    elif isinstance(response, str):
        response_text = response

    else:
        raise TypeError(f"不支持的 response 类型: {type(response)}")

    soup = BeautifulSoup(response_text, "html.parser")

    # 去除 \xa0
    for text_node in soup.find_all(string=True):
        if "\xa0" in text_node:
            text_node.replace_with(text_node.replace("\xa0", " "))

    # 删除注释
    for element in soup.find_all(string=lambda text: isinstance(text, Comment)):
        element.extract()

    soup_str = str(soup).replace("display:none;", "")
    root = etree.HTML(soup_str)
    if root is None:
        return ""

    if clear_font_style:
        for node in root.xpath("//*"):
            style_value = node.get("style")
            if isinstance(style_value, str):
                lower_style = style_value.lower()
                if "font-family" in lower_style:
                    node.set("style", lower_style.replace("font-family", ""))

    if rm_node_xpath:
        for rm_xpath in rm_node_xpath:
            for bad in root.xpath(rm_xpath):
                parent = bad.getparent()
                if parent is not None:
                    parent.remove(bad)

    if rm_href_xpath:
        for node in root.xpath(rm_href_xpath):
            node.attrib.pop("href", None)

    if replace_href_xpath and url:
        for element in root.xpath(replace_href_xpath):
            old_href = element.attrib.get("href")
            if old_href:
                element.attrib["href"] = urljoin(url, old_href)

    if replace_src_xpath and url:
        for element in root.xpath(replace_src_xpath):
            old_src = element.attrib.get("src")
            if old_src:
                element.attrib["src"] = urljoin(url, old_src)

    if replace_node_xpath:
        old_nodes = root.xpath(replace_node_xpath)
        for old_node in old_nodes:
            parent = old_node.getparent()
            if parent is None:
                continue
            old_node_str = html.tostring(old_node, encoding="unicode")
            new_node_str = f'<better-scroll :scroll-x="true" class="mt-5">{old_node_str}</better-scroll>'
            new_node = html.fromstring(new_node_str)
            parent.replace(old_node, new_node)

    content_node = root.xpath(content_xpath)
    if content_node:
        node_code_str = html.tostring(content_node[0], encoding="unicode")
        node_code = unescape(node_code_str)
        node_code = node_code.replace("\\r\\n", "").replace("\\t", "").strip()
        return node_code

    return ""

def re_parse(text, pattern=r'(\d{4}-\d{2}-\d{2})', placeholder=''):
    """
    正则匹配
    @param text:
    @param pattern: 正则表达式 默认匹配日期
    @param placeholder: 占位符默认为空
    """
    if text:
        result = re.findall(pattern, text)
        tuple_list = [i for item in result if isinstance(item, tuple) for i in item]
        match = [i for i in result if isinstance(i, str)]
        match.extend(tuple_list)
        result = placeholder.join(match) if match else None
        return result
    return None

def curl_cffi_request(url, headers=None, cookies=None, method="GET", params=None, data=None, json=None,
                      timeout=None, impersonate="chrome", request=None, proxies_type=False):
    from curl_cffi import requests
    from scrapy.http import HtmlResponse
    try:
        proxy = None
        if proxies_type:
            proxy = ScrapyProxy.get_long_proxy()

        logger.info(f"curl_cffi_request url: {url}  代理: {proxy}")

        resp = requests.request(
            method=method,
            url=url,
            headers=headers,
            cookies=cookies,
            params=params,
            data=data,
            json=json,
            timeout=timeout,
            impersonate=impersonate,
            proxy=proxy
        )
    except:
        return None

    return HtmlResponse(
        url=resp.url,
        body=resp.content,
        encoding=resp.encoding or "utf-8",
        request=request
    )


def common_request(
    url,
    headers=None,
    cookies=None,
    method="GET",
    params=None,
    data=None,
    json_data=None,
    timeout=30,
    proxies_type=False,
    verify=False,
    retry_times=2,       # 失败后最多重试次数
    retry_interval=2,    # 每次重试等待秒数
):
    import requests

    for attempt in range(retry_times + 1):
        proxies = None

        if proxies_type:
            proxy_ip = ScrapyProxy.get_long_proxy()
            proxies = {
                "http": proxy_ip,
                "https": proxy_ip,
            }

        try:
            logger.info(
                f"common_request 第 {attempt + 1}/{retry_times + 1} 次请求: "
                f"{url}，代理: {proxies}"
            )

            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                cookies=cookies,
                params=params,
                data=data,
                json=json_data,
                timeout=timeout,
                proxies=proxies,
                verify=verify,
            )

            # 2xx、3xx 直接返回；其余状态码进入重试
            if response.status_code not in {400, 401, 403, 404}:
                return response

            logger.warning(
                f"请求状态异常：status={response.status_code}，"
                f"第 {attempt + 1}/{retry_times + 1} 次，url={url}"
            )

        except requests.RequestException as e:
            logger.warning(
                f"请求异常：第 {attempt + 1}/{retry_times + 1} 次，"
                f"url={url}，reason={e}"
            )

        if attempt < retry_times:
            time.sleep(retry_interval)

    logger.error(f"请求重试结束仍失败：{url}")
    return None


# 加速乐
def get_jsl_cookies(url, proxies_type=False):
    proxies = None
    if proxies_type:
        proxy_ip = ScrapyProxy.get_long_proxy()
        proxies = {
            "http": proxy_ip,
            "https": proxy_ip,
        }
    headers = {
        "Host": urlparse(url).netloc,
        "Referer": url,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    }

    response = requests.get(url, headers=headers, proxies=proxies)
    # 用正则表达式获取 JavaScript 中的 document.cookie 的值。
    result = re.search(r'document\.cookie\=(.*?);location.href', response.text).group(1)
    # 转化为字典形式
    result_cookies = dict(response.cookies)
    # 执行 JavaScript 代码，将 result 中的 JavaScript 表达式求值
    create_cookies = execjs.eval(result)

    # 开始遍历 create_cookies 字符串，按分号切割成多个 cookie 片段
    for item in create_cookies.split(":"):
        # 将每个 cookie 片段按照等号切割，将切割结果作为字典的键和值，存储在 result_cookies 中
        result_cookies[item.split('=')[0]] = item.split('=')[1]

    headers = {
        "Host": urlparse(url).netloc,
        "Referer": url,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    }
    response = requests.get(url, headers=headers, cookies=result_cookies, proxies=proxies)
    # 这行获取当前的时间戳（秒级），赋值给变量 _0x1ba917。这个时间戳可能用于后续的计算。
    _0x1ba917 = int(time.time())

    # 哈希加密，接受一个参数 data，表示待加密的数据
    def generate_hash(data):
        # 使用 _0x888629 字典中的 'ha' 键进行条件判断，检查是否为 SHA-256 哈希算法
        if _0x888629['ha'] == 'sha256':
            # 如果算法为 SHA-256，则这行使用 hashlib 模块中的 sha256 方法对传入的数据进行编码（需将数据转换为字节类型），然后调用 hexdigest() 方法获取十六进制表示的哈希值。
            hash = hashlib.sha256(data.encode()).hexdigest()
        # 如果算法为 SHA-1.py，则进入这个分支
        elif _0x888629['ha'] == 'sha1':
            hash = hashlib.sha1(data.encode()).hexdigest()
        # 算法为 MD5
        elif _0x888629['ha'] == 'md5':
            hash = hashlib.md5(data.encode()).hexdigest()
        # 算法为 SHA-512
        elif _0x888629['ha'] == 'sha512':
            hash = hashlib.sha512(data.encode()).hexdigest()
        return hash

    def _0x142dd6(_0x1f119c, _0x234ddb):
        _0x4851ab = len(_0x888629['chars'])
        for _0x4fea55 in range(_0x4851ab):
            for _0x529f5a in range(_0x4851ab):
                _0x1fd754 = (_0x234ddb[0] + _0x888629['chars'][_0x4fea55]) + _0x888629['chars'][_0x529f5a] + \
                            _0x234ddb[
                                1]
                if generate_hash(_0x1fd754) == _0x1f119c:
                    return [_0x1fd754, int(time.time()) - _0x1ba917]

    data = re.findall(r'\;go\((.*?)\)</script>', response.text)
    # 提取到的数据列表不为空，那么解析数据为 JSON 格式
    if len(data) != 0:
        _0x888629 = json.loads(data[0])
        cookies = _0x142dd6(_0x888629['ct'], _0x888629['bts'])[0]
        result_cookies[_0x888629['tn']] = cookies

        result_response = requests.get(url, headers=headers, cookies=result_cookies, proxies=proxies)
        return result_response
    return None

# 固定ip
def get_seesion_proxies():
    proxy_ip = ScrapyProxy.get_long_proxy()
    proxies = {
        "http": proxy_ip,
        "https": proxy_ip,
    }
    return proxies