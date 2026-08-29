"""MinIO OSS 客户端 — 附件上传下载"""
import io
import os
import hashlib
from loguru import logger
from minio import Minio
from minio.error import S3Error
from config import MINIO_CONF


class OssClient:
    """MinIO 客户端单例"""

    _instance = None
    _bucket_checked = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            endpoint = MINIO_CONF['endpoint']
            cls._instance._client = Minio(
                endpoint,
                access_key=MINIO_CONF['access_key'],
                secret_key=MINIO_CONF['secret_key'],
                secure=MINIO_CONF['secure'],
                region=MINIO_CONF['region'],
            )
            logger.info(f"[OssClient] 已连接 MinIO: {endpoint} bucket={MINIO_CONF['bucket_name']}")
        return cls._instance

    @property
    def bucket(self):
        return MINIO_CONF['bucket_name']

    @property
    def client(self) -> Minio:
        return self._client

    def _ensure_bucket(self):
        if self._bucket_checked:
            return
        try:
            if not self._client.bucket_exists(self.bucket):
                self._client.make_bucket(self.bucket)
                logger.info(f"[OssClient] 创建 bucket: {self.bucket}")
        except Exception as e:
            logger.warning(f"[OssClient] bucket 检查失败: {e}")
        self._bucket_checked = True

    def exists(self, object_name: str) -> bool:
        try:
            self._client.stat_object(self.bucket, object_name)
            return True
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return False
            raise

    def upload_bytes(self, data: bytes, object_name: str, content_type: str = 'application/octet-stream') -> str:
        """上传字节数据到 MinIO，返回完整路径"""
        self._ensure_bucket()
        self._client.put_object(
            bucket_name=self.bucket,
            object_name=object_name,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return f"oss://{self.bucket}/{object_name}"

    def upload_file(self, file_path: str, object_name: str, content_type: str = 'application/octet-stream') -> str:
        """上传本地文件到 MinIO"""
        self._ensure_bucket()
        self._client.fput_object(
            bucket_name=self.bucket,
            object_name=object_name,
            file_path=file_path,
            content_type=content_type,
        )
        return f"oss://{self.bucket}/{object_name}"

    def get_object_path(self, sub_type: str, filename: str) -> str:
        """生成 OSS 存储路径: files/{sub_type}/{md5[0:2]}/{md5[2:4]}/{filename}"""
        md5 = hashlib.md5(filename.encode()).hexdigest()
        return f"files/{sub_type}/{md5[:2]}/{md5[2:4]}/{filename}"


def get_oss_client() -> OssClient:
    return OssClient()
