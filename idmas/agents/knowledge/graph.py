# =============================================================================
# Knowledge SubGraph 构建
#
# 节点:
#   - vector_search: Milvus向量相似度检索
#   - keyword_search: ES BM25关键词检索
#   - graph_query: Neo4j图谱关系查询
#   - merge_context: 多源结果融合与排序
#   - rag_generate: 基于融合上下文的LLM生成
#   - finalize: 输出最终结果
#
# 流程:
#   [vector_search, keyword_search, graph_query] (并行) → merge_context
#   → rag_generate → finalize
# =============================================================================
