"""Knowledge SubGraph 状态定义。"""
from __future__ import annotations
from typing import Any
from typing_extensions import TypedDict


class KnowledgeState(TypedDict, total=False):
    query:           str
    labels:          list[dict[str, Any]] | None
    vector_results:  list[dict[str, Any]]
    keyword_results: list[dict[str, Any]]
    graph_results:   list[dict[str, Any]]
    merged_context:  str
    rag_answer:      str | None
    confidence:      float
    final_result:    dict[str, Any] | None
