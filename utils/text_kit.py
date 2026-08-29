"""文本处理工具"""
import re
import hashlib


def clean_text(text: str) -> str:
    """清理文本（去除多余空白、换行等）"""
    if not text:
        return ''
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_amount(text: str) -> str:
    """从文本中提取金额"""
    pattern = r'[\d,]+\.?\d*\s*(?:万|亿|元|美元|人民币)?'
    match = re.search(pattern, text)
    return match.group(0).strip() if match else ''


def extract_date(text: str) -> str:
    """从文本中提取日期"""
    patterns = [
        r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?',
        r'\d{4}\d{2}\d{2}',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return ''


def md5(text: str) -> str:
    """计算 MD5"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def truncate(text: str, max_len: int = 500, suffix: str = '...') -> str:
    """截断文本"""
    if not text or len(text) <= max_len:
        return text
    return text[:max_len] + suffix


def remove_html_tags(text: str) -> str:
    """移除 HTML 标签"""
    return re.sub(r'<[^>]+>', '', text).strip()
