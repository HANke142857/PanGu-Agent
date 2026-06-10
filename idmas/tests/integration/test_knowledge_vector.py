"""
知识 SubGraph + 向量检索 集成测试。

验证默认内存 KB 检索、自定义向量库注入、无命中兜底。
"""

from __future__ import annotations

import pytest

from idmas.agents.knowledge.graph import build_knowledge_graph
from idmas.infrastructure.vectordb.base import (
    HashingEmbedder,
    InMemoryVectorClient,
    VectorItem,
)
from idmas.infrastructure.vectordb.milvus_client import KNOWLEDGE_COLLECTION


class TestDefaultMemoryKB:
    async def test_known_label_hits_knowledge(self):
        graph = build_knowledge_graph()
        result = await graph.ainvoke({
            "query": "轴承座是什么",
            "labels": [{"label_id": "1", "name": "轴承座"}],
        })
        final = result.get("final_result") or {}
        assert final.get("rag_answer")
        assert "轴承座" in final["rag_answer"]
        assert final["source_count"] >= 1

    async def test_unknown_label_falls_back(self):
        graph = build_knowledge_graph()
        result = await graph.ainvoke({
            "query": "未知部件",
            "labels": [{"label_id": "9", "name": "ZZZ不存在的部件名"}],
        })
        final = result.get("final_result") or {}
        assert final["source_count"] == 0
        assert final["rag_answer"] == "未找到相关知识。"


class TestInjectedVectorClient:
    async def test_custom_client_used(self):
        emb = HashingEmbedder(dim=256)
        client = InMemoryVectorClient()
        client.add(KNOWLEDGE_COLLECTION, [
            VectorItem(
                id="法兰盘",
                embedding=emb.embed_one("法兰盘"),
                metadata={"text": "法兰盘", "knowledge": "用于管道连接的圆盘状零件。"},
            ),
        ])

        graph = build_knowledge_graph(vector_client=client, embedder=emb)
        result = await graph.ainvoke({
            "query": "法兰盘用途",
            "labels": [{"label_id": "1", "name": "法兰盘"}],
        })
        final = result.get("final_result") or {}
        assert "管道连接" in final["rag_answer"]
        # 默认 KB 的条目不应出现（用的是注入的客户端）
        assert "轴承座" not in final["rag_answer"]
