"""
PLM 回写 API 集成测试：完成任务 → 回写 → 幂等；状态校验；Webhook。
"""

from __future__ import annotations

import hashlib
import hmac
import io
import uuid

import pytest
from fastapi.testclient import TestClient

from idmas.api.app import create_app
from idmas.infrastructure.adapters.base import FakePLMAdapter
from idmas.infrastructure.db.memory_repositories import (
    InMemoryAnalysisTaskRepository,
    InMemoryDrawingRepository,
)
from idmas.infrastructure.llm.vllm_client import FakeVLLMClient

WEBHOOK_SECRET = "test-secret"


@pytest.fixture()
def plm_adapter():
    return FakePLMAdapter(webhook_secret=WEBHOOK_SECRET)


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


def _completed_task(client) -> str:
    """上传图纸 → 建任务 →（如需）人工审核，返回 completed 任务 id。"""
    up = client.post(
        "/api/v1/drawings",
        data={"title": "齿轮箱图"},
        files={"file": ("g.png", io.BytesIO(b"PNG"), "image/png")},
    )
    drawing_id = up.json()["id"]
    create = client.post("/api/v1/tasks", json={"drawing_id": drawing_id, "question": "识别"})
    info = create.json()
    task_id = info["task_id"]
    if info["status"] == "waiting_review":
        client.post(f"/api/v1/tasks/{task_id}/review", json={
            "reviews": [{"label_id": "1", "action": "confirm"}]
        })
    return task_id


class TestWriteback:
    def test_writeback_then_idempotent(self, client, plm_adapter):
        task_id = _completed_task(client)

        r1 = client.post("/api/v1/plm/writeback", json={
            "task_id": task_id, "target_system": "teamcenter",
        })
        assert r1.status_code == 200
        body = r1.json()
        assert body["success"] is True and body["skipped"] is False
        assert len(plm_adapter.writebacks) == 1

        # 再次回写 → 幂等跳过，不重复写入
        r2 = client.post("/api/v1/plm/writeback", json={
            "task_id": task_id, "target_system": "teamcenter",
        })
        assert r2.json()["skipped"] is True
        assert len(plm_adapter.writebacks) == 1

    def test_writeback_task_not_found(self, client):
        r = client.post("/api/v1/plm/writeback", json={
            "task_id": str(uuid.uuid4()), "target_system": "teamcenter",
        })
        assert r.status_code == 404

    def test_writeback_incomplete_task_rejected(self, client):
        # 新建任务若处于 waiting_review，则不应允许回写
        up = client.post(
            "/api/v1/drawings",
            data={"title": "图"},
            files={"file": ("a.png", io.BytesIO(b"PNG"), "image/png")},
        )
        create = client.post("/api/v1/tasks", json={"drawing_id": up.json()["id"], "question": "q"})
        info = create.json()
        if info["status"] == "completed":
            pytest.skip("任务已完成，无法构造未完成场景")
        r = client.post("/api/v1/plm/writeback", json={
            "task_id": info["task_id"], "target_system": "teamcenter",
        })
        assert r.status_code >= 400


class TestWebhook:
    def test_valid_signature_accepted(self, client):
        payload = b'{"event":"doc_updated"}'
        sig = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
        r = client.post(
            "/api/v1/plm/webhook",
            content=payload,
            headers={"x-plm-system": "teamcenter", "x-plm-signature": sig},
        )
        assert r.status_code == 200
        assert r.json()["received"] is True

    def test_invalid_signature_rejected(self, client):
        r = client.post(
            "/api/v1/plm/webhook",
            content=b"{}",
            headers={"x-plm-signature": "bad"},
        )
        assert r.status_code == 401
