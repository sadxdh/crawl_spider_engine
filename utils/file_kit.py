import os
import io
import requests
import platform
import pdfkit
import pdfplumber
import playwright
from urllib.parse import urljoin
from bs4 import BeautifulSoup, Comment
from html import unescape
from lxml import etree, html
from docx import Document
from loguru import logger
import pandas as pd

from spire.doc import FileFormat, Document as Doc
from spire.doc.common import Stream

# from config import OSS_UPLOAD_SERVER
#
# def upload_file(content: bytes, file_type: str, file_name: str):
#     """oss 文件上传"""
#     headers = {'accept': '*/*'}
#     suffix = get_suffix(file_name).replace('.', '')
#     files = {'file': (file_name, content, f'application/{suffix}')}
#     url = '/'.join([OSS_UPLOAD_SERVER, file_type, file_name])
#     for _ in range(5):
#         response = requests.post(url=url, headers=headers, files=files)
#         try:
#             result = response.json()
#             return result['file_url']
#         except Exception as e:
#             logger.error(f'文件上传，解析结果失败：{e}')
#             continue
#     return None


def html_to_pdf(html_code):
    try:
        charset = '<head><meta charset="UTF-8">'
        if platform.system().lower() == 'windows':
            return pdfkit.from_string(charset + html_code,
                                      output_path=False,
                                      options={'encoding': 'utf-8', "enable-local-file-access": True})
        else:
            return pdfkit.from_string(charset + html_code,
                                      output_path=False,
                                      options={'encoding': 'utf-8', "enable-local-file-access": True})
    except Exception as e:
        raise Exception(f'html转为pdf时发生错误: {e}')


def get_node_html(response,
                  content_xpath: str,
                  clear_font_style: bool = False,
                  rm_node_xpath: list = None,
                  rm_href_xpath: str = False,
                  replace_href_xpath: str = False,
                  replace_node_xpath: str = False,
                  replace_src_xpath: str = False):
    """
    获取节点 html 代码
    :param replace_src_xpath: 替换src链接
    :param replace_node_xpath: 替换整个标签
    :param replace_href_xpath: 替换href为完成的url
    :param rm_href_xpath: 删除href属性
    :param rm_node_xpath: 移除指定节点
    :param clear_font_style: 清除字体格式
    :param response: response 对象
    :param content_xpath: 内容xpath  str
    :return: node_code
    """
    if isinstance(response, requests.models.Response):
        url = response.url
        response = response.content.decode('utf8')
    if isinstance(response, playwright.sync_api._generated.APIResponse):
        url = response.url
        response = response.body().decode('utf8')

    soup = BeautifulSoup(response, 'html.parser')

    # 去除xa0
    for text_node in soup.find_all(text=True):
        if '\xa0' in text_node:
            text_node.replace_with(text_node.replace('\xa0', ' '))

    # 删除 html 中的注释代码
    for element in soup(text=lambda text: isinstance(text, Comment)):
        element.extract()

    soup = str(soup).replace('display:none;', '')
    root = etree.HTML(soup)

    if clear_font_style:
        for node in root.xpath('//*'):
            style_value = node.get('style')
            if isinstance(style_value, str):
                style_value = style_value.lower()
            if style_value and 'font-family' in style_value:
                node.set('style', style_value.replace('font-family', ''))

    if rm_node_xpath:
        for rm_xpath in rm_node_xpath:
            for bad in root.xpath(rm_xpath):
                bad.getparent().remove(bad)

    if rm_href_xpath:
        for node in root.xpath(rm_href_xpath):
            node.attrib.pop('href')

    if replace_href_xpath:
        elements = root.xpath(replace_href_xpath)
        for element in elements:
            old_href = element.attrib['href']
            new_href = urljoin(url, old_href)
            element.attrib['href'] = new_href

    if replace_src_xpath:
        elements = root.xpath(replace_src_xpath)
        for element in elements:
            old_src = element.attrib['src']
            new_src = urljoin(url, old_src)
            element.attrib['src'] = new_src

    if replace_node_xpath:
        old_nodes = root.xpath(replace_node_xpath)
        for old_node in old_nodes:
            old_node_str = html.tostring(old_node).decode('utf-8')
            new_node_str = '<better-scroll :scroll-x="true" class="mt-5">' + old_node_str + '</better-scroll>'
            new_node = html.fromstring(new_node_str)
            old_node.getparent().replace(old_node, new_node)

    content_node = root.xpath(content_xpath)
    if content_node:
        content_node = content_node[0]
        node_code_str = html.tostring(content_node).decode('utf8')
        node_code = unescape(node_code_str)
        node_code = node_code.replace('\\r\\n', '').replace('\\t', '').strip()
        return node_code
    return ''


def get_suffix(file_name, suffix=True):
    """
    It returns the suffix of a file name
    :@param file_name: The name of the file
    :@param suffix: if suffix is true return suffix of file_name
    :return: The suffix of the file name.
    """
    result = os.path.splitext(file_name)
    res = result[1] if suffix else result[0]
    return res


def get_content_length(url):
    try:
        response = requests.head(url=url)
        if response:
            content_length = int(response.headers.get('Content-Length'))
            return content_length
    except:
        return None


def extract_pdf_table(content: bytes):
    """解析pdf表格"""
    pdf = pdfplumber.open(io.BytesIO(content))
    tables = [page.extract_table() for page in pdf.pages if page.extract_table()]
    return tables


def extract_pdf_text(content: bytes):
    """解析pdf表格"""
    pdf = pdfplumber.open(io.BytesIO(content))
    text_list = [page.extract_text() for page in pdf.pages]
    return text_list


def extract_docx_table(content: bytes):
    """解析docx表格"""
    doc = Document(io.BytesIO(content))
    tables = doc.tables
    return tables

def extract_docx_text(content: bytes):
    """解析docx段落文本"""
    doc = Document(io.BytesIO(content))
    text_list = [para.text.strip() for para in doc.paragraphs if 'Evaluation Warning' not in para.text]
    return text_list

def extract_xlsx_text(content: bytes, input_format='xlsx', output_format='json', **kwargs):
    """解析excel文本"""
    if input_format == 'csv':
        df = pd.read_csv(io.BytesIO(content))
    else:
        df = pd.read_excel(io.BytesIO(content))

    # 格式转换
    format_mapping = {
        "string": lambda: df.to_string(index=False).replace('NaN', ''),
        "csv": lambda: df.to_csv(index=False, **kwargs),
        "json": lambda: df.to_json(orient="records", force_ascii=False, **kwargs),
        "html": lambda: df.to_html(index=False, **kwargs)
    }

    return format_mapping[output_format.lower()]()

def convert_doc_to_docx(content: bytes) -> bytes:
    """Spire.Doc支持从内存加载"""
    doc = Doc()
    # 使用 Spire 的 Stream 封装字节内容
    stream_in = Stream(content)
    # 加载 .doc 格式的流（注意第二个参数是 FileFormat.Doc）
    doc.LoadFromStream(stream_in, FileFormat.Doc)
    # 创建输出流保存 .docx
    output_stream = Stream()
    # 保存为 Docx 格式到内存流
    doc.SaveToStream(output_stream, FileFormat.Docx)
    # 获取转换后的字节数据
    return bytes(output_stream.ToArray())  # ← 注意这里可能是 ToArray() 返回 byte[]
