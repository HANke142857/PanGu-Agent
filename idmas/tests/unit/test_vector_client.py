"""
向量库与嵌入器单元测试。
"""

from __future__ import annotations

import pytest

from idmas.infrastructure.vectordb.base import (
    HashingEmbedder,
    InMemoryVectorClient,
    VectorItem,
    cosine_similarity,
)
from idmas.infrastructure.vectordb.milvus_client import (
    KNOWLEDGE_COLLECTION,
    MilvusVectorClient,
)


class TestHashingEmbedder:
    def test_deterministic_and_dim(self):
        emb = HashingEmbedder(dim=128)
        v1 = emb.embed_one("轴承座")
        v2 = emb.embed_one("轴承座")
        assert v1 == v2
        assert len(v1) == 128

    def test_identical_text_cosine_one(self):
        emb = HashingEmbedder()
        a = emb.embed_one("齿轮箱")
        assert cosine_similarity(a, a) == pytest.approx(1.0)

    def test_disjoint_text_low_similarity(self):
        emb = HashingEmbedder()
        a = emb.embed_one("轴承座")     # 与"密封圈"无公共字符
        b = emb.embed_one("密封圈")
        assert cosine_similarity(a, b) < 0.2

    def test_empty_text_zero_vector(self):
        emb = HashingEmbedder(dim=32)
        v = emb.embed_one("")
        assert v == [0.0] * 32


class TestInMemoryVectorClient:
    @pytest.fixture()
    def seeded(self):
        emb = HashingEmbedder(dim=128)
        client = InMemoryVectorClient()
        client.add("c", [
            VectorItem(id="轴承座", embedding=emb.embed_one("轴承座"), metadata={"k": "A"}),
            VectorItem(id="密封圈", embedding=emb.embed_one("密封圈"), metadata={"k": "B"}),
        ])
        return emb, client

    async def test_search_ranks_exact_match_first(self, seeded):
        emb, client = seeded
        hits = await client.search("c", emb.embed_one("轴承座"), top_k=5)
        assert hits[0].id == "轴承座"
        assert hits[0].score == pytest.approx(1.0)
        assert hits[0].metadata["k"] == "A"

    async def test_min_score_filter(self, seeded):
        emb, client = seeded
        hits = await client.search("c", emb.embed_one("密封圈"), top_k=5, min_score=0.99)
        assert [h.id for h in hits] == ["密封圈"]

    async def test_top_k_limit(self, seeded):
        emb, client = seeded
        hits = await client.search("c", emb.embed_one("轴承座"), top_k=1, min_score=0.0)
        assert len(hits) == 1

    async def test_insert_upsert_and_delete(self, seeded):
        emb, client = seeded
        await client.insert("c", [
            VectorItem(id="轴承座", embedding=emb.embed_one("轴承座"), metadata={"k": "A2"}),
        ])
        assert client.count == 2          # upsert，不新增
        await client.delete("c", ["密封圈"])
        assert client.count == 1

    async def test_search_empty_collection(self, seeded):
        emb, client = seeded
        assert await client.search("missing", emb.embed_one("x")) == []


class TestMilvusClientConstruction:
    def test_construct_without_pymilvus_connection(self):
        # 仅构造不应触发 pymilvus 导入/连接
        c = MilvusVectorClient(host="h", port=19530, dim=768)
        assert c._collection_name == KNOWLEDGE_COLLECTION
        assert c._connected is False
