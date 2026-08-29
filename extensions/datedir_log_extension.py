"""日志路由扩展 - 将 Scrapyd 日志重定向到日期子目录

生产环境目录结构：
  CRAWL_LOG_DIR/{project}/{spider_name}/{YYYY-MM-DD}/{job_id}.log

Scrapyd 默认将日志写到 logs/{project}/{spider}/{job}.log（不含日期层）。
此扩展在 spider_opened 信号时，把 Scrapy root logger 的 FileHandler
替换为指向日期子目录的新路径，使归档 job 能按目录日期直接判断日龄。

仅在检测到 LOG_FILE 环境变量时生效（Scrapyd 调度时自动注入），
本地直接 scrapy crawl 不影响。
"""
import logging
import os
from datetime import date
from pathlib import Path

from scrapy import signals


class DateDirLogExtension:

    @classmethod
    def from_crawler(cls, crawler):
        ext = cls()
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        return ext

    def spider_opened(self, spider):
        log_file = os.environ.get('SCRAPY_LOG_FILE') or _find_file_handler_path()
        if not log_file:
            return  # 本地运行，无文件 handler，跳过

        log_path = Path(log_file)
        # 已经在日期子目录下（路径含 YYYY-MM-DD 段），无需处理
        if _is_date_dir(log_path.parent):
            return

        # 目标路径：{原目录}/{YYYY-MM-DD}/{原文件名}
        date_dir = log_path.parent / date.today().isoformat()
        date_dir.mkdir(parents=True, exist_ok=True)
        new_path = date_dir / log_path.name

        # 替换 root logger 中的 FileHandler
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            if isinstance(handler, logging.FileHandler):
                if Path(handler.baseFilename).resolve() == log_path.resolve():
                    handler.close()
                    root_logger.removeHandler(handler)
                    new_handler = logging.FileHandler(new_path, encoding='utf-8')
                    new_handler.setFormatter(handler.formatter)
                    new_handler.setLevel(handler.level)
                    root_logger.addHandler(new_handler)
                    break


def _find_file_handler_path() -> str | None:
    """从 root logger 现有 FileHandler 中取路径"""
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.FileHandler):
            return handler.baseFilename
    return None


def _is_date_dir(path: Path) -> bool:
    """判断目录名是否为 YYYY-MM-DD 格式"""
    try:
        date.fromisoformat(path.name)
        return True
    except ValueError:
        return False
