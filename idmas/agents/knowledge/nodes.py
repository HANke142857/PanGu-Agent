"""
Knowledge Agent 节点（MVP：内置知识库存根）。
生产环境替换为 Milvus + Elasticsearch + Neo4j 三路检索。
"""
from __future__ import annotations
from typing import Any
from idmas.agents.knowledge.state import KnowledgeState

# MVP 内置知识条目（生产环境换成真实向量库检索）
_FAKE_KB: dict[str, str] = {
    "轴承座":  "支撑旋转轴的固定部件，材料通常为铸铁或铸钢，需定期润滑。",
    "齿轮箱":  "变速传动装置，由齿轮系组成，需检查油位和密封性。",
    "输出轴":  "将动力传递到外部负载的轴，注意轴端密封和联轴器对中精度。",
    "轴承":    "减少摩擦的支撑元件，包括滚动轴承和滑动轴承，需关注磨损和温升。",
    "密封圈":  "防止泄漏的密封元件，使用寿命受温度和压力影响。",
}


def vector_search_node(state: KnowledgeState) -> dict[str, Any]:
    """MVP: 从内置字典按关键词匹配，模拟向量检索。"""
    labels  = state.get("labels") or []
    results = []
    for lbl in labels:
        name = str(lbl.get("name", ""))
        for kb_name, desc in _FAKE_KB.items():
            if kb_name in name or name in kb_name:
                results.append({"label": name, "knowledge": desc, "source": "fake_kb", "score": 0.92})
    return {"vector_results": results}


def keyword_search_node(state: KnowledgeState) -> dict[str, Any]:
    """MVP: 同向量检索复用，生产替换为 Elasticsearch BM25。"""
    return {"keyword_results": []}   # 暂时返回空，避免重复


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
    answer  = f"根据知识库：\n{context}" if context else "未找到相关知识。"
    return {"rag_answer": answer, "confidence": 0.88 if context else 0.30}


def knowledge_finalize_node(state: KnowledgeState) -> dict[str, Any]:
    return {
        "final_result": {
            "rag_answer":      state.get("rag_answer"),
            "confidence":      state.get("confidence", 0.0),
            "source_count":    len(state.get("vector_results") or []),
            "merged_context":  state.get("merged_context"),
        }
    }
