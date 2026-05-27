# =============================================================================
# 知识检索 Pydantic Schema
#
# 请求Schema:
#   - KnowledgeSearchRequest: 知识检索请求
#     - query: str (必填)
#     - top_k: int (默认5, 范围1-20)
#     - search_type: vector | keyword | hybrid (默认 hybrid)
#
# 响应Schema:
#   - KnowledgeSearchResponse: 检索结果
#     - results: list[KnowledgeResult]
#       - doc_id: str
#       - title: str
#       - content: str
#       - score: float
#       - source: str (vector/keyword/graph)
#       - tags: list[str]
#     - total: int
#     - search_type: str
# =============================================================================
