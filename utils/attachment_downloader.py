"""
附件下载 + MinIO 上传工具类

用法：爬虫中直接调用

    from utils.attachment_downloader import AttachmentDownloader

    class MySpider(BaseSpider):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.downloader = AttachmentDownloader(self.name, self.data_table)

        def parse_detail(self, response):
            ...
            # 下载附件并上传 OSS
            result = self.downloader.download_and_upload(url, title)
            item['oss_attachment_list'] = json.dumps([result], ensure_ascii=False)
            item['oss_folder'] = result.get('oss_full_path', '').rsplit('/', 1)[0]

            # 或批量处理
            results = self.downloader.process_urls([
                ('https://example.com/a.pdf', '报告A'),
                ('https://example.com/b.doc', '报告B'),
            ])

状态码规范（与 05-多附件字段存储与状态管理规范 对齐）：
  1      — 成功
  404    — 附件不存在/链接失效
  503    — 源站不可用
  1001   — 需要验证码
  1002   — 需要登录/Cookie
  1003   — 响应异常（返回 HTML 而非文件）
  1004   — 文件扩展名与 Content-Type 不匹配
  1005   — PDF 降级（图片型 PDF）
  5001   — MinIO 上传失败
  5002   — 下载超时
  5003   — 下载请求异常
  5004   — 文件大小为 0
  5005   — 文件超过大小限制
"""
import hashlib
import os
import threading
from datetime import datetime
from typing import Optional

import requests
from loguru import logger

from utils.oss_client import get_oss_client

_SESSION_TIMEOUT = 30
_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

_MIME_EXT = {
    'application/pdf': 'pdf',
    'application/msword': 'doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'application/vnd.ms-excel': 'xls',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    'application/zip': 'zip',
    'image/jpeg': 'jpg', 'image/png': 'png', 'image/gif': 'gif',
}


def _md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _detect_ext(url: str, content_type: str = '') -> str:
    """推断文件扩展名：优先 URL 后缀 → Content-Type"""
    path = url.split('?')[0].split('#')[0]
    _, ext = os.path.splitext(path)
    ext = ext.lstrip('.').lower()
    if ext and len(ext) <= 5:
        return ext
    return _MIME_EXT.get(content_type, 'bin')


class AttachmentDownloader:
    """附件下载器（线程安全）"""

    def __init__(self, spider_name: str = '', table_name: str = ''):
        self.spider_name = spider_name
        self.table_name = table_name
        self._oss = get_oss_client()
        self._session: Optional[requests.Session] = None
        self._lock = threading.Lock()
        self.stats = {'downloaded': 0, 'failed': 0}

    def _get_session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36',
            })
        return self._session

    # ------------------------------------------------------------------ #
    # 公开 API                                                            #
    # ------------------------------------------------------------------ #
    def download(self, url: str, headers: dict = None, timeout: int = _SESSION_TIMEOUT) -> tuple:
        """下载单个附件，返回 (content: bytes, content_type: str, status_code: int)"""
        if not url or not url.startswith('http'):
            return b'', '', 400

        session = self._get_session()
        try:
            resp = session.get(url, timeout=timeout, allow_redirects=True,
                               headers=headers or {})
        except requests.exceptions.Timeout:
            return b'', '', 5002
        except requests.exceptions.ConnectionError:
            return b'', '', 503
        except requests.exceptions.RequestException as e:
            logger.warning(f"[AttachmentDownloader] 下载异常: {url} → {e}")
            return b'', '', 5003

        if resp.status_code != 200:
            return b'', '', resp.status_code

        return resp.content, resp.headers.get('Content-Type', '').split(';')[0].strip().lower(), 200

    def upload(self, data: bytes, filename: str, content_type: str = 'application/octet-stream') -> str:
        """上传数据到 MinIO，返回 OSS 路径"""
        table = self.table_name or self.spider_name or 'attachments'
        today = datetime.now().strftime('%Y%m%d')
        md5 = _md5_bytes(data)
        object_name = f"files/{table}/{today}/{md5[:2]}/{md5[2:4]}/{filename}"
        oss_url = self._oss.upload_bytes(data, object_name, content_type=content_type)
        with self._lock:
            self.stats['downloaded'] += 1
        return oss_url

    def download_and_upload(self, url: str, title: str = '',
                             headers: dict = None) -> dict:
        """下载单个附件并上传 MinIO，返回 oss_attachment_list 条目"""
        if not title:
            title = url.split('/')[-1].split('?')[0]

        result = {
            'original_title': title,
            'source_url': url,
            'status': 0,
            'oss_file_name': None,
            'oss_full_path': None,
            'file_extension': '',
        }

        # Step 1: 下载
        content, content_type, status = self.download(url, headers=headers)
        if status != 200:
            result['status'] = status
            with self._lock:
                self.stats['failed'] += 1
            return result

        # Step 2: 校验
        if len(content) == 0:
            result['status'] = 5004
            return result
        if len(content) > _MAX_FILE_SIZE:
            result['status'] = 5005
            return result
        if content_type == 'text/html' or content.strip().startswith((b'<!DOCTYPE', b'<html')):
            result['status'] = 1003
            return result

        # Step 3: 确定扩展名 + 文件名
        ext = _detect_ext(url, content_type)
        filename = f"{_md5_bytes(content)[:16]}.{ext}"
        result['file_extension'] = ext

        # Step 4: 上传 OSS
        try:
            oss_url = self.upload(content, filename, content_type)
            result['status'] = 1
            result['oss_file_name'] = filename
            result['oss_full_path'] = oss_url
        except Exception as e:
            logger.error(f"[AttachmentDownloader] MinIO 上传失败: {url} → {e}")
            result['status'] = 5001
            with self._lock:
                self.stats['failed'] += 1

        return result

    def process_urls(self, url_title_pairs: list, headers: dict = None) -> list:
        """批量处理多个附件 URL（顺序执行），返回 oss_attachment_list"""
        results = []
        for url, title in url_title_pairs:
            results.append(self.download_and_upload(url, title, headers=headers))
        return results

    def close(self):
        """关闭会话"""
        if self._session:
            self._session.close()
            self._session = None
