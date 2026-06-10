"""
Pytest 全局 Fixtures（可复用，各测试也可自定义覆盖）。

提供内存仓储 + FakeVLLM 的 API TestClient，无需数据库/网络/GPU。
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
def fake_llm():
    return FakeVLLMClient()


@pytest.fixture()
def drawing_repo():
    return InMemoryDrawingRepository()


@pytest.fixture()
def task_repo():
    return InMemoryAnalysisTaskRepository()


@pytest.fixture()
def api_client(fake_llm, drawing_repo, task_repo):
    app = create_app(llm_client=fake_llm, drawing_repo=drawing_repo, task_repo=task_repo)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
