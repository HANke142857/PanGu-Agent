# =============================================================================
# Knowledge SubGraph 状态定义 (KnowledgeState)
#
# 状态字段:
#   - query: str                        # 检索查询
#   - labels: list[dict] | None         # 相关标号(用于上下文)
#   - vector_results: list[dict]        # Milvus向量检索结果
#   - keyword_results: list[dict]       # ES关键词检索结果
#   - graph_results: list[dict]         # Neo4j图谱查询结果
#   - merged_context: str               # 融合后的上下文
#   - rag_answer: str | None            # RAG生成的回答
#   - confidence: float                 # 回答置信度
#   - final_result: dict | None         # 最终结果
# =============================================================================
