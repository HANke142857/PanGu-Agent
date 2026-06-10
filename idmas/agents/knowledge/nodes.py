"""
Knowledge Agent 节点。

向量检索（vector_search）通过注入的 BaseVectorClient + BaseEmbedder 完成，
默认走内存向量库（预置 KB），生产注入 MilvusVectorClient（见 graph.build_knowledge_graph）。
keyword/graph 检索仍为存根，后续接 Elasticsearch / Neo4j。
"""
from __future__ import annotations

from typing import Any

from idmas.agents.knowledge.state import KnowledgeState
from idmas.infrastructure.vectordb.base import BaseEmbedder, BaseVectorClient


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
        labels = state.get("labels") or []
        # 无标号时退化为对 query 本身检索
        queries = [str(lbl.get("name", "")) for lbl in labels] or [state.get("query") or ""]

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


def keyword_search_node(state: KnowledgeState) -> dict[str, Any]:
    """MVP: 返回空，生产替换为 Elasticsearch BM25。"""
    return {"keyword_results": []}


def graph_query_node(state: KnowledgeState) -> dict[str, Any]:
    """MVP: 返回空图谱结果，生产替换为 Neo4j 查询。"""
    return {"graph_results": []}


def merge_context_node(state: KnowledgeState) -> dict[str, Any]:
    """融合多源结果生成 RAG 上下文。"""
    all_results = (state.get("vector_results") or []) + (state.get("keyword_results") or [])
    if not all_results:
        return {"merged_context": "暂无相关知识库条目。"}
    lines = [f"- {r['label']}: {r['knowledge']}" for r in all_results]
    return {"merged_context": "\n".join(lines)}


def rag_generate_node(state: KnowledgeState) -> dict[str, Any]:
    """MVP: 基于融合上下文直接返回，生产替换为 LLM 生成。"""
    context = state.get("merged_context") or ""
    has_kb  = bool(state.get("vector_results") or state.get("keyword_results"))
    answer  = f"根据知识库：\n{context}" if has_kb else "未找到相关知识。"
    return {"rag_answer": answer, "confidence": 0.88 if has_kb else 0.30}


def knowledge_finalize_node(state: KnowledgeState) -> dict[str, Any]:
    return {
        "final_result": {
            "rag_answer":      state.get("rag_answer"),
            "confidence":      state.get("confidence", 0.0),
            "source_count":    len(state.get("vector_results") or []),
            "merged_context":  state.get("merged_context"),
        }
    }
