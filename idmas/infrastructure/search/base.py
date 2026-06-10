"""
全文检索抽象（RAG 的关键词/BM25 通道）。

    BaseSearchClient     : 抽象接口
    InMemorySearchClient : 测试/开发用，基于字符 token 重叠打分（无需 ES）
    ESSearchClient       : 生产实现，见 es_client.py（需 Elasticsearch）

与向量检索互补：向量擅长语义，关键词擅长精确术语/编号匹配。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

KNOWLEDGE_INDEX = "idmas-knowledge"


def tokenize(text: str) -> set[str]:
    """字符 uni/bi-gram 分词，适配中文短词。"""
    text = (text or "").strip()
    if not text:
        return set()
    chars = list(text)
    bigrams = [text[i : i + 2] for i in range(len(text) - 1)]
    return set(chars) | set(bigrams)


class SearchHit(BaseModel):
    id:       str
    score:    float
    text:     str = ""
    metadata: dict = Field(default_factory=dict)


class BaseSearchClient(ABC):
    @abstractmethod
    async def ensure_indices(self) -> None:
        ...

    @abstractmethod
    async def index_document(self, index: str, doc_id: str, body: dict) -> None:
        ...

    @abstractmethod
    async def search(self, index: str, query: str, top_k: int = 5, min_score: float = 0.0) -> list[SearchHit]:
        ...

    async def bulk_index(self, index: str, documents: list[dict]) -> None:
        for doc in documents:
            await self.index_document(index, str(doc.get("id")), doc)

    async def health_check(self) -> bool:
        return True


class InMemorySearchClient(BaseSearchClient):
    """进程内全文检索：token 重叠比例打分，归一化到 [0, 1]。"""

    def __init__(self) -> None:
        # index -> doc_id -> (text, metadata, tokens)
        self._store: dict[str, dict[str, tuple[str, dict, set[str]]]] = {}

    def add(self, index: str, doc_id: str, text: str, metadata: dict | None = None) -> None:
        self._store.setdefault(index, {})[doc_id] = (text, metadata or {}, tokenize(text))

    async def ensure_indices(self) -> None:
        return None

    async def index_document(self, index: str, doc_id: str, body: dict) -> None:
        text = str(body.get("text") or body.get("content") or body.get("name") or "")
        self.add(index, doc_id, text, body)

    async def search(self, index: str, query: str, top_k: int = 5, min_score: float = 0.0) -> list[SearchHit]:
        qtokens = tokenize(query)
        if not qtokens:
            return []
        hits: list[SearchHit] = []
        for doc_id, (text, metadata, dtokens) in self._store.get(index, {}).items():
            overlap = len(qtokens & dtokens)
            if overlap == 0:
                continue
            score = overlap / len(qtokens)
            if score >= min_score:
                hits.append(SearchHit(id=doc_id, score=round(score, 4), text=text, metadata=metadata))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]
