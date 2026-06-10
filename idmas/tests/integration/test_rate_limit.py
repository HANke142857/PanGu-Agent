"""
限流中间件集成测试（opt-in，内存缓存计数）。
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from idmas.api.app import create_app
from idmas.config.settings import get_settings
from idmas.infrastructure.db.memory_repositories import (
    InMemoryAnalysisTaskRepository,
    InMemoryDrawingRepository,
)
from idmas.infrastructure.llm.vllm_client import FakeVLLMClient


@pytest.fixture()
def client(monkeypatch):
    # 启用限流并把阈值调到很低，便于触发
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "3")
    get_settings.cache_clear()
    app = create_app(
        llm_client=FakeVLLMClient(),
        drawing_repo=InMemoryDrawingRepository(),
        task_repo=InMemoryAnalysisTaskRepository(),
    )
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    get_settings.cache_clear()        # 复位，避免污染其它测试


class TestRateLimit:
    def test_blocks_after_threshold(self, client):
        # 前 3 次放行，第 4 次 429
        codes = [client.get("/api/v1/health").status_code for _ in range(4)]
        assert codes[:3] == [200, 200, 200]
        assert codes[3] == 429

    def test_429_body_and_header(self, client):
        for _ in range(3):
            client.get("/api/v1/health")
        resp = client.get("/api/v1/health")
        assert resp.status_code == 429
        assert resp.headers.get("Retry-After") == "60"
        assert resp.json()["error"]["code"] == "IDMAS-429-001"
