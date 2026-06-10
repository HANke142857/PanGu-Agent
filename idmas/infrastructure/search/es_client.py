"""
Elasticsearch 全文检索客户端（生产）。

实现 BaseSearchClient。elasticsearch 异步客户端惰性导入——仅实例化并访问时
才需要安装，测试用 InMemorySearchClient 不受影响。

索引（参见技术设计 6.3）：idmas-knowledge（content/text + tags）。
降级：Milvus 不可用时，Knowledge Agent 可仅用本通道（BM25）兜底。
"""

from __future__ import annotations

import logging

from idmas.infrastructure.search.base import BaseSearchClient, SearchHit

logger = logging.getLogger(__name__)


class ESSearchClient(BaseSearchClient):
    def __init__(self, url: str) -> None:
        self._url = url
        self._client = None

    def _get_client(self):
        if self._client is None:
            from elasticsearch import AsyncElasticsearch  # 惰性导入

            self._client = AsyncElasticsearch(self._url)
        return self._client

    async def ensure_indices(self) -> None:
        from idmas.infrastructure.search.base import KNOWLEDGE_INDEX

        client = self._get_client()
        if not await client.indices.exists(index=KNOWLEDGE_INDEX):
            await client.indices.create(
                index=KNOWLEDGE_INDEX,
                mappings={
                    "properties": {
                        "text":    {"type": "text"},
                        "content": {"type": "text"},
                        "tags":    {"type": "keyword"},
                    }
                },
            )
            logger.info("ES index %s 已创建", KNOWLEDGE_INDEX)

    async def index_document(self, index: str, doc_id: str, body: dict) -> None:
        await self._get_client().index(index=index, id=doc_id, document=body)

    async def search(self, index: str, query: str, top_k: int = 5, min_score: float = 0.0) -> list[SearchHit]:
        client = self._get_client()
        resp = await client.search(
            index=index,
            query={"multi_match": {"query": query, "fields": ["text", "content", "name"]}},
            size=top_k,
        )
        hits: list[SearchHit] = []
        for h in resp.get("hits", {}).get("hits", []):
            score = float(h.get("_score") or 0.0)
            if score < min_score:
                continue
            src = h.get("_source", {})
            hits.append(SearchHit(
                id=str(h.get("_id")),
                score=score,
                text=str(src.get("text") or src.get("content") or ""),
                metadata=src,
            ))
        return hits

    async def health_check(self) -> bool:
        try:
            return bool(await self._get_client().ping())
        except Exception:  # noqa: BLE001
            return False

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None
