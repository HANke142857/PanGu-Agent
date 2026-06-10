"""
Milvus 向量数据库客户端（生产）。

实现 BaseVectorClient。pymilvus 惰性导入——仅实例化并连接时才需要安装，
测试用 InMemoryVectorClient 不受影响。

Collection（知识检索单元，dim 与 EMBEDDING_DIM 一致）::

    knowledge_docs : 知识文档/标号 Embedding
      schema: id(VARCHAR PK), embedding(FLOAT_VECTOR), text(VARCHAR), payload(JSON)
      index : HNSW, COSINE, M=16, efConstruction=200

约定：metadata 整体序列化进 payload(JSON) 字段，检索时还原，避免 schema 频繁变更。
"""

from __future__ import annotations

import json
import logging

from idmas.infrastructure.vectordb.base import BaseVectorClient, VectorHit, VectorItem

logger = logging.getLogger(__name__)

KNOWLEDGE_COLLECTION = "knowledge_docs"
_TEXT_MAX = 4096
_PAYLOAD_MAX = 8192


class MilvusVectorClient(BaseVectorClient):
    """基于 pymilvus 的向量库客户端。"""

    def __init__(
        self,
        host: str,
        port: int,
        dim: int,
        collection: str = KNOWLEDGE_COLLECTION,
    ) -> None:
        self._host = host
        self._port = port
        self._dim = dim
        self._collection_name = collection
        self._connected = False

    # ------------------------------------------------------------------
    # 连接与建表
    # ------------------------------------------------------------------

    def _connect(self) -> None:
        if self._connected:
            return
        from pymilvus import connections  # 惰性导入

        connections.connect(alias="default", host=self._host, port=str(self._port))
        self._connected = True

    async def ensure_collections(self) -> None:
        from pymilvus import (  # 惰性导入
            Collection,
            CollectionSchema,
            DataType,
            FieldSchema,
            utility,
        )

        self._connect()
        if utility.has_collection(self._collection_name):
            return

        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self._dim),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=_TEXT_MAX),
            FieldSchema(name="payload", dtype=DataType.VARCHAR, max_length=_PAYLOAD_MAX),
        ]
        schema = CollectionSchema(fields, description="IDMAS 知识检索向量集")
        coll = Collection(name=self._collection_name, schema=schema)
        coll.create_index(
            field_name="embedding",
            index_params={
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 16, "efConstruction": 200},
            },
        )
        coll.load()
        logger.info("Milvus collection %s 已创建并加载", self._collection_name)

    # ------------------------------------------------------------------
    # 读写
    # ------------------------------------------------------------------

    async def insert(self, collection: str, items: list[VectorItem]) -> list[str]:
        from pymilvus import Collection  # 惰性导入

        await self.ensure_collections()
        coll = Collection(collection)
        rows = [
            {
                "id": it.id,
                "embedding": it.embedding,
                "text": str(it.metadata.get("text", ""))[:_TEXT_MAX],
                "payload": json.dumps(it.metadata, ensure_ascii=False)[:_PAYLOAD_MAX],
            }
            for it in items
        ]
        coll.insert(rows)
        coll.flush()
        return [it.id for it in items]

    async def search(
        self,
        collection: str,
        embedding: list[float],
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[VectorHit]:
        from pymilvus import Collection  # 惰性导入

        self._connect()
        coll = Collection(collection)
        coll.load()
        results = coll.search(
            data=[embedding],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"ef": 64}},
            limit=top_k,
            output_fields=["payload"],
        )
        hits: list[VectorHit] = []
        for hit in results[0]:
            if hit.score < min_score:
                continue
            payload = hit.entity.get("payload") if hasattr(hit, "entity") else None
            metadata = json.loads(payload) if payload else {}
            hits.append(VectorHit(id=str(hit.id), score=float(hit.score), metadata=metadata))
        return hits

    async def delete(self, collection: str, ids: list[str]) -> None:
        from pymilvus import Collection  # 惰性导入

        self._connect()
        coll = Collection(collection)
        expr = "id in [" + ", ".join(f'"{i}"' for i in ids) + "]"
        coll.delete(expr)

    async def close(self) -> None:
        if not self._connected:
            return
        from pymilvus import connections  # 惰性导入

        connections.disconnect("default")
        self._connected = False
