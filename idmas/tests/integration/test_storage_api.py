"""
图纸文件存储 API 集成测试：上传落库 → 下载取回原始字节。
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from idmas.api.app import create_app
from idmas.infrastructure.db.memory_repositories import (
    InMemoryAnalysisTaskRepository,
    InMemoryDrawingRepository,
)
from idmas.infrastructure.llm.vllm_client import FakeVLLMClient
from idmas.infrastructure.storage.base import InMemoryStorageClient


@pytest.fixture()
def storage():
    return InMemoryStorageClient()


@pytest.fixture()
def client(storage):
    app = create_app(
        llm_client=FakeVLLMClient(),
        drawing_repo=InMemoryDrawingRepository(),
        task_repo=InMemoryAnalysisTaskRepository(),
        storage=storage,
    )
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestUploadStoresFile:
    def test_upload_then_download(self, client, storage):
        content = b"\x89PNG\r\n REAL BYTES"
        resp = client.post(
            "/api/v1/drawings",
            data={"title": "齿轮箱图", "drawing_type": "assembly"},
            files={"file": ("gear.png", io.BytesIO(content), "image/png")},
        )
        assert resp.status_code == 201
        data = resp.json()
        drawing_id = data["id"]
        # 文件已真正写入存储
        assert storage.count == 1
        # file_url 不再是占位 memory://<uuid>/...（现由存储返回）
        assert data["file_url"].startswith("memory://idmas-drawings/")

        # 下载取回与上传一致的字节
        dl = client.get(f"/api/v1/drawings/{drawing_id}/file")
        assert dl.status_code == 200
        assert dl.content == content
        assert dl.headers["content-type"].startswith("image/png")

    def test_download_unknown_drawing_404(self, client):
        import uuid
        resp = client.get(f"/api/v1/drawings/{uuid.uuid4()}/file")
        assert resp.status_code == 404
