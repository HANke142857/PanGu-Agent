"""
端到端全流程测试（内存后端，无 DB/网络/GPU）。

覆盖主链路：上传图纸 → 创建任务 → （低置信度走人工审核）→ 查询结果
→ 完成后 PLM 回写（幂等）→ 知识检索。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from idmas.api.app import create_app
from idmas.infrastructure.adapters.base import FakePLMAdapter
from idmas.infrastructure.db.memory_repositories import (
    InMemoryAnalysisTaskRepository,
    InMemoryDrawingRepository,
)
from idmas.infrastructure.llm.vllm_client import FakeVLLMClient
from idmas.tests.fixtures.sample_data import upload_file


@pytest.fixture()
def plm_adapter():
    return FakePLMAdapter()


@pytest.fixture()
def client(plm_adapter):
    app = create_app(
        llm_client=FakeVLLMClient(),
        drawing_repo=InMemoryDrawingRepository(),
        task_repo=InMemoryAnalysisTaskRepository(),
        plm_factory=lambda system: plm_adapter,
    )
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestFullFlow:
    def test_upload_to_writeback_to_knowledge(self, client, plm_adapter):
        # 1) 上传图纸（触发 Vision，存储落地）
        up = client.post(
            "/api/v1/drawings",
            data={"title": "齿轮箱装配图", "drawing_type": "assembly"},
            files=upload_file("gear.png"),
        )
        assert up.status_code == 201
        drawing_id = up.json()["id"]
        assert up.json()["label_count"] >= 1

        # 2) 创建解析任务
        create = client.post("/api/v1/tasks", json={
            "drawing_id": drawing_id, "question": "识别所有标号",
        })
        assert create.status_code == 202
        info = create.json()
        task_id = info["task_id"]

        # 3) 低置信度 → 人工审核 → 完成
        if info["status"] == "waiting_review":
            rev = client.post(f"/api/v1/tasks/{task_id}/review", json={
                "reviews": [{"label_id": "1", "action": "confirm"}]
            })
            assert rev.status_code == 200

        detail = client.get(f"/api/v1/tasks/{task_id}")
        assert detail.status_code == 200
        assert detail.json()["status"] == "completed"

        # 4) PLM 回写 + 幂等
        wb1 = client.post("/api/v1/plm/writeback", json={
            "task_id": task_id, "target_system": "teamcenter"})
        assert wb1.status_code == 200 and wb1.json()["success"] is True
        wb2 = client.post("/api/v1/plm/writeback", json={
            "task_id": task_id, "target_system": "teamcenter"})
        assert wb2.json()["skipped"] is True
        assert len(plm_adapter.writebacks) == 1

        # 5) 文件可下载
        dl = client.get(f"/api/v1/drawings/{drawing_id}/file")
        assert dl.status_code == 200 and len(dl.content) > 0

        # 6) 知识检索
        ks = client.post("/api/v1/knowledge/search", json={"query": "轴承座"})
        assert ks.status_code == 200
        assert ks.json()["total"] >= 1

    def test_drawing_not_found_flow(self, client):
        import uuid
        resp = client.post("/api/v1/tasks", json={"drawing_id": str(uuid.uuid4())})
        assert resp.status_code == 404
