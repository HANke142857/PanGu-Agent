"""
MinIO 对象存储客户端（生产）。

实现 BaseStorageClient。minio SDK 惰性导入——仅实例化并访问时才需要安装，
测试用 InMemoryStorageClient 不受影响。minio SDK 为同步 API，统一用
asyncio.to_thread 包装，避免阻塞事件循环。

配置：MINIO_ENDPOINT / MINIO_ACCESS_KEY / MINIO_SECRET_KEY / MINIO_BUCKET。
"""

from __future__ import annotations

import asyncio
import io
import logging
from datetime import timedelta

from idmas.infrastructure.storage.base import (
    BaseStorageClient,
    ObjectNotFoundError,
    guess_content_type,
)

logger = logging.getLogger(__name__)


class MinioStorageClient(BaseStorageClient):
    """基于 MinIO SDK 的对象存储客户端。"""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ) -> None:
        self._endpoint = endpoint
        self._access_key = access_key
        self._secret_key = secret_key
        self._bucket = bucket
        self._secure = secure
        self._client = None

    def _get_client(self):
        if self._client is None:
            from minio import Minio  # 惰性导入

            self._client = Minio(
                self._endpoint,
                access_key=self._access_key,
                secret_key=self._secret_key,
                secure=self._secure,
            )
        return self._client

    async def ensure_bucket(self) -> None:
        def _ensure() -> None:
            client = self._get_client()
            if not client.bucket_exists(self._bucket):
                client.make_bucket(self._bucket)
                logger.info("MinIO bucket %s 已创建", self._bucket)

        await asyncio.to_thread(_ensure)

    async def upload(self, data: bytes, object_name: str, content_type: str | None = None) -> str:
        ctype = content_type or guess_content_type(object_name)

        def _put() -> None:
            client = self._get_client()
            client.put_object(
                self._bucket,
                object_name,
                io.BytesIO(data),
                length=len(data),
                content_type=ctype,
            )

        await self.ensure_bucket()
        await asyncio.to_thread(_put)
        return await self.get_presigned_url(object_name)

    async def download(self, object_name: str) -> bytes:
        def _get() -> bytes:
            from minio.error import S3Error  # 惰性导入

            client = self._get_client()
            try:
                resp = client.get_object(self._bucket, object_name)
                try:
                    return resp.read()
                finally:
                    resp.close()
                    resp.release_conn()
            except S3Error as exc:
                raise ObjectNotFoundError(object_name) from exc

        return await asyncio.to_thread(_get)

    async def get_presigned_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        def _url() -> str:
            client = self._get_client()
            return client.presigned_get_object(
                self._bucket, object_name, expires=timedelta(seconds=expires_seconds)
            )

        return await asyncio.to_thread(_url)

    async def delete(self, object_name: str) -> None:
        def _del() -> None:
            self._get_client().remove_object(self._bucket, object_name)

        await asyncio.to_thread(_del)

    async def health_check(self) -> bool:
        try:
            return await asyncio.to_thread(lambda: self._get_client().bucket_exists(self._bucket))
        except Exception:  # noqa: BLE001
            return False
