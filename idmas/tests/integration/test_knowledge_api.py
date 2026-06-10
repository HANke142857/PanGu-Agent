"""
知识检索 API 集成测试。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from idmas.api.app import create_app
from idmas.infrastructure.db.memory_repositories import (
    InMemoryAnalysisTaskRepository,
    InMemoryDrawingRepository,
)
from idmas.infrastructure.llm.vllm_client import FakeVLLMClient


@pytest.fixture()
def client():
    app = create_app(
        llm_client=FakeVLLMClient(),
        drawing_repo=InMemoryDrawingRepository(),
        task_repo=InMemoryAnalysisTaskRepository(),
    )
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestKnowledgeSearch:
    def test_hybrid_returns_results(self, client):
        resp = client.post("/api/v1/knowledge/search", json={"query": "轴承座"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["search_type"] == "hybrid"
        assert data["total"] >= 1
        contents = " ".join(r["content"] for r in data["results"])
        assert "轴承座" in contents or "支撑" in contents
        # 图谱通道应带出设备/故障
        sources = {r["source"] for r in data["results"]}
        assert "graph" in sources or "vector" in sources

    def test_graph_only(self, client):
        resp = client.post("/api/v1/knowledge/search",
                           json={"query": "轴承座", "search_type": "graph"})
        assert resp.status_code == 200
        for r in resp.json()["results"]:
            assert r["source"] == "graph"

    def test_unknown_query_empty(self, client):
        resp = client.post("/api/v1/knowledge/search",
                           json={"query": "ZZZ不存在的部件名"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_top_k_caps_results(self, client):
        resp = client.post("/api/v1/knowledge/search",
                           json={"query": "轴承座", "top_k": 1})
        assert resp.status_code == 200
        assert len(resp.json()["results"]) <= 1

    def test_empty_query_rejected(self, client):
        resp = client.post("/api/v1/knowledge/search", json={"query": ""})
        assert resp.status_code == 422
