# =============================================================================
# Knowledge SubGraph 节点函数
#
# 节点函数:
#   - vector_search_node(state: KnowledgeState) -> dict
#     调用Milvus进行向量相似度检索 (label_vectors / drawing_vectors)
#
#   - keyword_search_node(state: KnowledgeState) -> dict
#     调用Elasticsearch进行BM25关键词检索 (idmas-labels / idmas-knowledge)
#
#   - graph_query_node(state: KnowledgeState) -> dict
#     调用Neo4j查询标号→部件→设备→故障关系链
#
#   - merge_context_node(state: KnowledgeState) -> dict
#     融合多源检索结果，去重排序，构建LLM上下文
#
#   - rag_generate_node(state: KnowledgeState) -> dict
#     基于融合上下文调用LLM生成回答
#
#   - finalize_node(state: KnowledgeState) -> dict
#     汇总知识检索结果
# =============================================================================
