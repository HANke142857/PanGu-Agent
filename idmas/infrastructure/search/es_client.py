# =============================================================================
# Elasticsearch 全文检索客户端
#
# 职责:
#   - 管理ES连接
#   - 全文检索、索引管理
#
# 配置:
#   - ES_URL: ES地址 (http://localhost:9200)
#
# 索引 (参见技术设计6.3节):
#   - idmas-drawings: 图纸搜索
#     映射: title(text) + metadata(object)
#   - idmas-labels: 标号模糊匹配
#     映射: name(text+keyword) + synonyms(text)
#   - idmas-knowledge: RAG的BM25通道
#     映射: content(text) + tags(keyword)
#
# 方法:
#   - search(index, query, top_k) -> list[dict]
#   - index_document(index, doc_id, body) -> None
#   - bulk_index(index, documents) -> None
#   - ensure_indices() -> None  # 启动时创建/校验索引
#   - health_check() -> bool
#
# 降级策略: Milvus不可用时，Knowledge Agent降级为ES关键词检索
# =============================================================================
