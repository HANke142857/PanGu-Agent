"""Knowledge SubGraph 构建。"""
from __future__ import annotations
from langgraph.graph import END, START, StateGraph
from idmas.agents.knowledge.state import KnowledgeState
from idmas.agents.knowledge.nodes import (
    vector_search_node, keyword_search_node, graph_query_node,
    merge_context_node, rag_generate_node, knowledge_finalize_node,
)


def build_knowledge_graph():
    builder = StateGraph(KnowledgeState)
    builder.add_node("vector_search",   vector_search_node)
    builder.add_node("keyword_search",  keyword_search_node)
    builder.add_node("graph_query",     graph_query_node)
    builder.add_node("merge_context",   merge_context_node)
    builder.add_node("rag_generate",    rag_generate_node)
    builder.add_node("finalize",        knowledge_finalize_node)
    builder.add_edge(START,             "vector_search")
    builder.add_edge("vector_search",   "keyword_search")
    builder.add_edge("keyword_search",  "graph_query")
    builder.add_edge("graph_query",     "merge_context")
    builder.add_edge("merge_context",   "rag_generate")
    builder.add_edge("rag_generate",    "finalize")
    builder.add_edge("finalize",        END)
    return builder.compile()
