"""
对象存储抽象。

与项目其它基础设施一致（抽象接口 + Fake + 真实实现）::

    BaseStorageClient     : 抽象接口，业务只依赖它
    InMemoryStorageClient : 测试/开发用，字节存进程内 dict（无需 MinIO）
    MinioStorageClient    : 生产实现，见 minio_client.py（需 MinIO）

object_name 约定：``{drawing_id}/{filename}``，作为存储内的稳定键；
file_url 由 upload 返回，用于展示/下载入口。
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod

# 文件扩展名 → MIME 类型
CONTENT_TYPES: dict[str, str] = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "pdf": "application/pdf",
    "dwg": "application/acad",
    "dxf": "application/dxf",
}


def guess_content_type(object_name: str) -> str:
    suffix = object_name.rsplit(".", 1)[-1].lower() if "." in object_name else ""
    return CONTENT_TYPES.get(suffix, "application/octet-stream")


class ObjectNotFoundError(Exception):
    """存储中不存在该对象。"""


class BaseStorageClient(ABC):
    """对象存储抽象接口。"""

    @abstractmethod
    async def ensure_bucket(self) -> None:
        """确保默认 Bucket 存在（幂等）。"""
        ...

    @abstractmethod
    async def upload(self, data: bytes, object_name: str, content_type: str | None = None) -> str:
        """上传字节，返回可用于展示/下载的 URL。"""
        ...

    @abstractmethod
    async def download(self, object_name: str) -> bytes:
        """下载对象字节；不存在抛 ObjectNotFoundError。"""
        ...

    @abstractmethod
    async def get_presigned_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        """生成限时访问 URL。"""
        ...

    @abstractmethod
    async def delete(self, object_name: str) -> None:
        ...

    async def health_check(self) -> bool:
        return True

    @staticmethod
    def compute_sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()


class InMemoryStorageClient(BaseStorageClient):
    """进程内对象存储：object_name -> (bytes, content_type)。"""

    def __init__(self, bucket: str = "idmas-drawings") -> None:
        self._bucket = bucket
        self._store: dict[str, tuple[bytes, str]] = {}

    async def ensure_bucket(self) -> None:
        return None

    async def upload(self, data: bytes, object_name: str, content_type: str | None = None) -> str:
        self._store[object_name] = (data, content_type or guess_content_type(object_name))
        return f"memory://{self._bucket}/{object_name}"

    async def download(self, object_name: str) -> bytes:
        if object_name not in self._store:
            raise ObjectNotFoundError(object_name)
        return self._store[object_name][0]

    async def get_presigned_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        return f"memory://{self._bucket}/{object_name}"

    async def delete(self, object_name: str) -> None:
        self._store.pop(object_name, None)

    def content_type_of(self, object_name: str) -> str:
        return self._store[object_name][1] if object_name in self._store else guess_content_type(object_name)

    @property
    def count(self) -> int:
        return len(self._store)
