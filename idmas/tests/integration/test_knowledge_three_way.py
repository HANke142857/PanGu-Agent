"""
知识 SubGraph 三路检索（向量 + 关键词 + 图谱）集成测试。
"""

from __future__ import annotations

import pytest

from idmas.agents.knowledge.graph import build_knowledge_graph
from idmas.infrastructure.graphdb.base import InMemoryGraphClient
from idmas.infrastructure.search.base import KNOWLEDGE_INDEX, InMemorySearchClient


class TestDefaultThreeWay:
    async def test_known_label_merges_three_sources(self):
        graph = build_knowledge_graph()
        result = await graph.ainvoke({
            "query": "轴承座相关信息",
            "labels": [{"label_id": "1", "name": "轴承座"}],
        })
        final = result.get("final_result") or {}
        answer = final["rag_answer"]
        # 向量/关键词：描述；图谱：设备 + 故障
        assert "轴承座" in answer
        assert "减速器" in answer          # 来自图谱通道
        assert "F001" in answer            # 来自图谱故障
        assert final["source_count"] >= 2  # 多路命中

    async def test_unknown_label_all_empty(self):
        graph = build_knowledge_graph()
        result = await graph.ainvoke({
            "query": "未知",
            "labels": [{"label_id": "9", "name": "ZZZ不存在的部件"}],
        })
        final = result.get("final_result") or {}
        assert final["source_count"] == 0
        assert final["rag_answer"] == "未找到相关知识。"


class TestInjectedClients:
    async def test_custom_search_and_graph(self):
        search = InMemorySearchClient()
        search.add(KNOWLEDGE_INDEX, "法兰盘", text="法兰盘", metadata={"knowledge": "管道连接件"})

        graph_client = InMemoryGraphClient()
        graph_client.seed("法兰盘", "不锈钢", "管路系统", ["F100 法兰渗漏"])

        graph = build_knowledge_graph(search_client=search, graph_client=graph_client)
        result = await graph.ainvoke({
            "query": "法兰盘",
            "labels": [{"label_id": "1", "name": "法兰盘"}],
        })
        answer = (result.get("final_result") or {})["rag_answer"]
        assert "管道连接件" in answer     # 关键词通道
        assert "管路系统" in answer        # 图谱通道
        assert "F100" in answer
