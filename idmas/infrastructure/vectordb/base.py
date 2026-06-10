"""
向量库抽象。

与项目其它基础设施一致（抽象接口 + Fake + 真实实现）::

    BaseVectorClient     : 抽象接口，知识检索只依赖它
    InMemoryVectorClient : 测试/开发用，进程内余弦相似度检索（无需 Milvus）
    MilvusVectorClient   : 生产实现，见 milvus_client.py（需 Milvus）

    BaseEmbedder    : 文本 → 向量 抽象
    HashingEmbedder : 确定性哈希嵌入，无需模型/GPU，供测试与离线开发；
                      生产替换为真实 Embedding 模型（如 bge / vLLM embedding）

设计取舍：嵌入与检索解耦——节点先用 embedder 把查询文本转向量，再交给
向量客户端检索，这样切换 Milvus 时业务代码不动。
"""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

class VectorItem(BaseModel):
    """写入向量库的一条记录。"""

    id:        str
    embedding: list[float]
    metadata:  dict = Field(default_factory=dict)


class VectorHit(BaseModel):
    """检索命中结果。"""

    id:       str
    score:    float                       # 余弦相似度，[-1, 1]，越大越相似
    metadata: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# 嵌入器
# ---------------------------------------------------------------------------

class BaseEmbedder(ABC):
    """文本嵌入抽象。"""

    @property
    @abstractmethod
    def dim(self) -> int:
        ...

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


class HashingEmbedder(BaseEmbedder):
    """
    确定性哈希嵌入：把文本切成字符 uni/bi-gram，哈希到固定维度的桶并计数，
    再 L2 归一化。相同文本 → 相同向量；相关文本（共享字符）→ 较高余弦。

    优点：零依赖、确定、可复现，适合测试与离线；缺点：无语义泛化，
    生产请替换为真实 Embedding 模型。
    """

    def __init__(self, dim: int = 768) -> None:
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def _tokens(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
        chars = list(text)
        bigrams = [text[i : i + 2] for i in range(len(text) - 1)]
        return chars + bigrams

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self._dim
            for tok in self._tokens(text):
                h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
                vec[h % self._dim] += 1.0
            norm = math.sqrt(sum(v * v for v in vec))
            if norm > 0:
                vec = [v / norm for v in vec]
            out.append(vec)
        return out


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"维度不匹配: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# ---------------------------------------------------------------------------
# 向量客户端
# ---------------------------------------------------------------------------

class BaseVectorClient(ABC):
    """向量库抽象接口。"""

    @abstractmethod
    async def ensure_collections(self) -> None:
        """创建/校验所需 Collection（幂等）。"""
        ...

    @abstractmethod
    async def insert(self, collection: str, items: list[VectorItem]) -> list[str]:
        """批量写入，返回写入的 id 列表。"""
        ...

    @abstractmethod
    async def search(
        self,
        collection: str,
        embedding: list[float],
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[VectorHit]:
        """向量相似度检索，按 score 降序，过滤掉低于 min_score 的命中。"""
        ...

    @abstractmethod
    async def delete(self, collection: str, ids: list[str]) -> None:
        ...

    async def close(self) -> None:
        return None


class InMemoryVectorClient(BaseVectorClient):
    """进程内向量库：dict[collection] -> list[VectorItem]，纯 Python 余弦检索。"""

    def __init__(self) -> None:
        self._store: dict[str, list[VectorItem]] = {}

    # 同步种子写入，供 graph 构建（同步上下文）预置知识库使用。
    def add(self, collection: str, items: list[VectorItem]) -> list[str]:
        bucket = self._store.setdefault(collection, [])
        ids: list[str] = []
        for item in items:
            existing = next((i for i, it in enumerate(bucket) if it.id == item.id), None)
            if existing is not None:
                bucket[existing] = item
            else:
                bucket.append(item)
            ids.append(item.id)
        return ids

    async def ensure_collections(self) -> None:
        return None

    async def insert(self, collection: str, items: list[VectorItem]) -> list[str]:
        return self.add(collection, items)

    async def search(
        self,
        collection: str,
        embedding: list[float],
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[VectorHit]:
        bucket = self._store.get(collection, [])
        scored = [
            VectorHit(id=it.id, score=cosine_similarity(embedding, it.embedding), metadata=it.metadata)
            for it in bucket
        ]
        scored = [h for h in scored if h.score >= min_score]
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:top_k]

    async def delete(self, collection: str, ids: list[str]) -> None:
        bucket = self._store.get(collection)
        if not bucket:
            return
        idset = set(ids)
        self._store[collection] = [it for it in bucket if it.id not in idset]

    @property
    def count(self) -> int:
        return sum(len(v) for v in self._store.values())
