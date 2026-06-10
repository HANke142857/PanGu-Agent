"""
全文检索 + 知识图谱 客户端单元测试。
"""

from __future__ import annotations

import pytest

from idmas.infrastructure.graphdb.base import GraphRelations, InMemoryGraphClient
from idmas.infrastructure.graphdb.neo4j_client import Neo4jGraphClient
from idmas.infrastructure.search.base import (
    KNOWLEDGE_INDEX,
    InMemorySearchClient,
    tokenize,
)
from idmas.infrastructure.search.es_client import ESSearchClient


class TestTokenize:
    def test_unigram_bigram(self):
        assert tokenize("轴承") == {"轴", "承", "轴承"}

    def test_empty(self):
        assert tokenize("") == set()


class TestInMemorySearch:
    @pytest.fixture()
    def client(self):
        c = InMemorySearchClient()
        c.add(KNOWLEDGE_INDEX, "轴承座", text="轴承座", metadata={"knowledge": "支撑旋转轴"})
        c.add(KNOWLEDGE_INDEX, "密封圈", text="密封圈", metadata={"knowledge": "防泄漏"})
        return c

    async def test_exact_match_top(self, client):
        hits = await client.search(KNOWLEDGE_INDEX, "轴承座")
        assert hits[0].id == "轴承座"
        assert hits[0].score == pytest.approx(1.0)
        assert hits[0].metadata["knowledge"] == "支撑旋转轴"

    async def test_disjoint_no_hit(self, client):
        hits = await client.search(KNOWLEDGE_INDEX, "法兰盘", min_score=0.34)
        assert hits == []

    async def test_partial_overlap(self, client):
        # "轴承" 的 token 全部包含于 "轴承座"
        hits = await client.search(KNOWLEDGE_INDEX, "轴承")
        assert hits and hits[0].id == "轴承座"

    async def test_index_document_and_bulk(self, client):
        await client.index_document(KNOWLEDGE_INDEX, "法兰盘", {"text": "法兰盘", "knowledge": "管道连接"})
        hits = await client.search(KNOWLEDGE_INDEX, "法兰盘")
        assert hits[0].metadata["knowledge"] == "管道连接"


class TestESConstruction:
    def test_construct_without_sdk(self):
        c = ESSearchClient("http://localhost:9200")
        assert c._client is None


class TestInMemoryGraph:
    @pytest.fixture()
    def client(self):
        c = InMemoryGraphClient()
        c.seed("轴承座", "HT250 铸铁", "减速器", ["F001 异响"])
        return c

    async def test_query_relations(self, client):
        rel = await client.query_label_relations("轴承座")
        assert rel is not None
        assert rel.material == "HT250 铸铁"
        assert rel.equipment == ["减速器"]
        assert rel.faults == ["F001 异响"]

    async def test_query_missing_returns_none(self, client):
        assert await client.query_label_relations("不存在") is None

    async def test_as_text(self, client):
        rel = await client.query_label_relations("轴承座")
        text = rel.as_text()
        assert "HT250" in text and "减速器" in text and "F001" in text

    async def test_async_write_methods(self):
        c = InMemoryGraphClient()
        await c.upsert_part("齿轮箱", "45# 钢")
        await c.link_part_to_equipment("齿轮箱", "传动总成")
        await c.add_fault("传动总成", "F012 漏油")
        rel = await c.query_label_relations("齿轮箱")
        assert rel.equipment == ["传动总成"]
        assert rel.faults == ["F012 漏油"]

    def test_empty_relations_as_text(self):
        assert GraphRelations(part="x").as_text() == ""


class TestNeo4jConstruction:
    def test_construct_without_driver(self):
        c = Neo4jGraphClient("bolt://localhost:7687", "neo4j", "pw")
        assert c._driver is None
