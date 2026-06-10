"""
Knowledge Agent 节点。

RAG 三路检索均为注入式（工厂模式），默认走内存实现（预置 KB），生产分别注入
Milvus / Elasticsearch / Neo4j（见 graph.build_knowledge_graph）：

  - vector_search : 语义相似（BaseVectorClient + BaseEmbedder）
  - keyword_search: 精确术语/编号（BaseSearchClient，BM25）
  - graph_query   : 部件-设备-故障关系链（BaseGraphClient）

三路结果在 merge_context 融合去重，交给 rag_generate。
"""
from __future__ import annotations

from typing import Any

from idmas.agents.knowledge.state import KnowledgeState
from idmas.infrastructure.graphdb.base import BaseGraphClient
from idmas.infrastructure.search.base import BaseSearchClient
from idmas.infrastructure.vectordb.base import BaseEmbedder, BaseVectorClient


def _label_queries(state: KnowledgeState) -> list[str]:
    labels = state.get("labels") or []
    return [str(lbl.get("name", "")) for lbl in labels] or [state.get("query") or ""]


def make_vector_search_node(
    vector_client: BaseVectorClient,
    embedder: BaseEmbedder,
    collection: str,
    top_k: int = 3,
    min_score: float = 0.55,
):
    """工厂：绑定向量客户端 + 嵌入器，生成 vector_search 节点。

    对每个标号名称做向量检索，命中结果归一化为
    {label, knowledge, source, score}，与下游 merge_context 约定一致。
    """

    async def vector_search_node(state: KnowledgeState) -> dict[str, Any]:
        queries = _label_queries(state)

        results: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for name in queries:
            if not name:
                continue
            embedding = embedder.embed_one(name)
            hits = await vector_client.search(
                collection, embedding, top_k=top_k, min_score=min_score
            )
            for hit in hits:
                knowledge = str(hit.metadata.get("knowledge", "")) or str(hit.metadata.get("text", ""))
                key = (name, hit.id)
                if not knowledge or key in seen:
                    continue
                seen.add(key)
                results.append({
                    "label":     name,
                    "knowledge": knowledge,
                    "source":    "vector",
                    "score":     round(hit.score, 4),
                })
        return {"vector_results": results}

    return vector_search_node


def make_keyword_search_node(
    search_client: BaseSearchClient,
    index: str,
    top_k: int = 3,
    min_score: float = 0.34,
):
    """工厂：绑定全文检索客户端，生成 keyword_search 节点（BM25 通道）。"""

    async def keyword_search_node(state: KnowledgeState) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for name in _label_queries(state):
            if not name:
                continue
            hits = await search_client.search(index, name, top_k=top_k, min_score=min_score)
            for hit in hits:
                knowledge = str(hit.metadata.get("knowledge", "")) or hit.text
                key = (name, hit.id)
                if not knowledge or key in seen:
                    continue
                seen.add(key)
                results.append({
                    "label":     name,
                    "knowledge": knowledge,
                    "source":    "keyword",
                    "score":     hit.score,
                })
        return {"keyword_results": results}

    return keyword_search_node


def make_graph_query_node(graph_client: BaseGraphClient):
    """工厂：绑定图谱客户端，生成 graph_query 节点（关系通道）。"""

    async def graph_query_node(state: KnowledgeState) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        for name in _label_queries(state):
            if not name:
                continue
            relations = await graph_client.query_label_relations(name)
            if relations is None:
                continue
            text = relations.as_text()
            if not text:
                continue
            results.append({
                "label":     name,
                "knowledge": text,
                "source":    "graph",
                "score":     1.0,
            })
        return {"graph_results": results}

    return graph_query_node


def _all_results(state: KnowledgeState) -> list[dict[str, Any]]:
    return (
        (state.get("vector_results") or [])
        + (state.get("keyword_results") or [])
        + (state.get("graph_results") or [])
    )


def merge_context_node(state: KnowledgeState) -> dict[str, Any]:
    """融合三路结果生成 RAG 上下文（按 label+knowledge 去重）。"""
    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    for r in _all_results(state):
        key = (r["label"], r["knowledge"])
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- {r['label']}: {r['knowledge']}")
    if not lines:
        return {"merged_context": "暂无相关知识库条目。"}
    return {"merged_context": "\n".join(lines)}


def rag_generate_node(state: KnowledgeState) -> dict[str, Any]:
    """MVP: 基于融合上下文直接返回，生产替换为 LLM 生成。"""
    context = state.get("merged_context") or ""
    has_kb  = bool(_all_results(state))
    answer  = f"根据知识库：\n{context}" if has_kb else "未找到相关知识。"
    return {"rag_answer": answer, "confidence": 0.88 if has_kb else 0.30}


def knowledge_finalize_node(state: KnowledgeState) -> dict[str, Any]:
    return {
        "final_result": {
            "rag_answer":      state.get("rag_answer"),
            "confidence":      state.get("confidence", 0.0),
            "source_count":    len(_all_results(state)),
            "merged_context":  state.get("merged_context"),
        }
    }
