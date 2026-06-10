"""
对象存储单元测试。
"""

from __future__ import annotations

import pytest

from idmas.infrastructure.storage.base import (
    InMemoryStorageClient,
    ObjectNotFoundError,
    guess_content_type,
)
from idmas.infrastructure.storage.minio_client import MinioStorageClient


class TestGuessContentType:
    @pytest.mark.parametrize("name,expected", [
        ("a/b.png", "image/png"),
        ("x.jpg", "image/jpeg"),
        ("doc.pdf", "application/pdf"),
        ("m.dwg", "application/acad"),
        ("noext", "application/octet-stream"),
    ])
    def test_mime(self, name, expected):
        assert guess_content_type(name) == expected


class TestInMemoryStorage:
    async def test_upload_download_roundtrip(self):
        s = InMemoryStorageClient()
        url = await s.upload(b"PNGDATA", "id1/a.png")
        assert url.startswith("memory://idmas-drawings/id1/a.png")
        assert await s.download("id1/a.png") == b"PNGDATA"
        assert s.content_type_of("id1/a.png") == "image/png"

    async def test_download_missing_raises(self):
        s = InMemoryStorageClient()
        with pytest.raises(ObjectNotFoundError):
            await s.download("nope")

    async def test_delete(self):
        s = InMemoryStorageClient()
        await s.upload(b"x", "k")
        assert s.count == 1
        await s.delete("k")
        assert s.count == 0
        with pytest.raises(ObjectNotFoundError):
            await s.download("k")

    async def test_sha256_stable(self):
        assert InMemoryStorageClient.compute_sha256(b"abc") == (
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        )

    async def test_presigned_url(self):
        s = InMemoryStorageClient()
        await s.upload(b"x", "k")
        assert "memory://idmas-drawings/k" in await s.get_presigned_url("k")


class TestMinioConstruction:
    def test_construct_without_minio_sdk(self):
        # 仅构造不应触发 minio SDK 导入/连接
        c = MinioStorageClient("h:9000", "ak", "sk", "bucket")
        assert c._bucket == "bucket"
        assert c._client is None
