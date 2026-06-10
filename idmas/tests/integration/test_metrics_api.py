"""
/metrics 端点 + 请求指标中间件 集成测试。
"""

from __future__ import annotations

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
    monkeypatch.setenv("METRICS_ENABLED", "true")
    get_settings.cache_clear()
    app = create_app(
        llm_client=FakeVLLMClient(),
        drawing_repo=InMemoryDrawingRepository(),
        task_repo=InMemoryAnalysisTaskRepository(),
    )
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    get_settings.cache_clear()


class TestMetricsEndpoint:
    def test_metrics_exposed_after_request(self, client):
        # 先打一个请求，产生指标
        assert client.get("/api/v1/health").status_code == 200
        resp = client.get("/metrics")
        assert resp.status_code == 200
        body = resp.text
        assert "idmas_request_total" in body
        # 路由模板而非原始路径（低基数）
        assert "/api/v1/health" in body

    def test_metrics_disabled_returns_empty(self, monkeypatch):
        monkeypatch.delenv("METRICS_ENABLED", raising=False)
        get_settings.cache_clear()
        app = create_app(
            llm_client=FakeVLLMClient(),
            drawing_repo=InMemoryDrawingRepository(),
            task_repo=InMemoryAnalysisTaskRepository(),
        )
        with TestClient(app) as c:
            c.get("/api/v1/health")
            resp = c.get("/metrics")
            assert resp.status_code == 200
            assert resp.text == ""        # NoopMetrics 渲染为空
        get_settings.cache_clear()
