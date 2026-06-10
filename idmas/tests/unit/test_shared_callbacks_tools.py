"""
shared.callbacks + shared.tools 单元测试。
"""

from __future__ import annotations

import pytest

from idmas.agents.shared.callbacks import AgentLoggingCallback
from idmas.agents.shared.tools import make_knowledge_search_tool, make_ocr_tool
from idmas.infrastructure.ocr.base import FakeOCRClient
from idmas.infrastructure.vectordb.base import (
    HashingEmbedder,
    InMemoryVectorClient,
    VectorItem,
)


class _RecordingMetrics:
    def __init__(self):
        self.agents: list[tuple[str, float]] = []

    def observe_agent(self, agent, duration_s):
        self.agents.append((agent, duration_s))


class TestAgentLoggingCallback:
    def test_chain_lifecycle_reports_metric(self):
        m = _RecordingMetrics()
        cb = AgentLoggingCallback(metrics=m)
        cb.on_chain_start({"name": "vision_agent"}, {})
        cb.on_chain_end({}, name="vision_agent")
        assert len(m.agents) == 1
        assert m.agents[0][0] == "vision_agent"
        assert m.agents[0][1] >= 0

    def test_error_is_safe(self):
        cb = AgentLoggingCallback()
        cb.on_chain_start({"name": "x"}, {})
        cb.on_chain_error(RuntimeError("boom"), name="x")   # 不应抛异常

    def test_no_metrics_ok(self):
        cb = AgentLoggingCallback()
        cb.on_chain_start(None, {"name": "n"})
        cb.on_chain_end({}, name="n")


class TestTools:
    async def test_knowledge_search_tool(self):
        emb = HashingEmbedder(dim=128)
        client = InMemoryVectorClient()
        client.add("kb", [VectorItem(id="轴承座", embedding=emb.embed_one("轴承座"),
                                      metadata={"knowledge": "支撑轴"})])
        tool = make_knowledge_search_tool(client, emb, collection="kb")
        assert tool.name == "search_knowledge_base"
        out = await tool.ainvoke({"query": "轴承座"})
        assert out and out[0]["id"] == "轴承座"
        assert out[0]["knowledge"] == "支撑轴"

    async def test_ocr_tool(self):
        tool = make_ocr_tool(FakeOCRClient())
        out = await tool.ainvoke({"image_url": "memory://x.png"})
        assert [w["text"] for w in out] == ["3", "输出轴"]
