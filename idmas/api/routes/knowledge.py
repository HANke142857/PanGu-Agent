"""
知识检索路由。

POST /api/v1/knowledge/search  对查询文本跑 RAG 三路检索（向量 + 关键词 + 图谱），
融合返回 Top-K。search_type 可只取某一路或 hybrid（全部）。

复用 agents.knowledge 子图（默认内存后端，按 settings 切 Milvus/ES/Neo4j）。
"""
from __future__ import annotations

from fastapi import APIRouter

from idmas.agents.knowledge.graph import build_knowledge_graph
from idmas.api.schemas.knowledge import (
    KnowledgeResult,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

_SOURCE_KEYS = {
    "vector":  ["vector_results"],
    "keyword": ["keyword_results"],
    "graph":   ["graph_results"],
    "hybrid":  ["vector_results", "keyword_results", "graph_results"],
}


@router.post("/search", response_model=KnowledgeSearchResponse, summary="知识检索（RAG 三路）")
async def knowledge_search(body: KnowledgeSearchRequest):
    graph = build_knowledge_graph()
    state = await graph.ainvoke({"query": body.query, "labels": [{"name": body.query}]})

    keys = _SOURCE_KEYS.get(body.search_type, _SOURCE_KEYS["hybrid"])
    seen: set[tuple[str, str]] = set()
    results: list[KnowledgeResult] = []
    for key in keys:
        for hit in state.get(key) or []:
            label = str(hit.get("label", ""))
            content = str(hit.get("knowledge", ""))
            dedup = (label, content)
            if not content or dedup in seen:
                continue
            seen.add(dedup)
            results.append(KnowledgeResult(
                doc_id=label,
                title=label,
                content=content,
                score=float(hit.get("score", 0.0)),
                source=str(hit.get("source", "")),
            ))

    results.sort(key=lambda r: r.score, reverse=True)
    results = results[: body.top_k]
    return KnowledgeSearchResponse(
        results=results, total=len(results), search_type=body.search_type,
    )
