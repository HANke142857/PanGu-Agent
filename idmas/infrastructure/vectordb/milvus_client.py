# =============================================================================
# Milvus 向量数据库客户端
#
# 职责:
#   - 管理Milvus连接与Collection
#   - 向量插入、检索、删除操作
#
# 配置:
#   - MILVUS_HOST / MILVUS_PORT: 连接地址
#
# Collections (参见技术设计3.3节):
#   - drawing_vectors: 图纸特征向量
#     schema: drawing_id(PK), embedding(FLOAT_VECTOR 1024), drawing_type
#     index: IVF_FLAT, COSINE, nlist=128
#
#   - label_vectors: 标号Embedding
#     schema: label_id(PK), drawing_id, name, embedding(FLOAT_VECTOR 768)
#     index: HNSW, COSINE, M=16, efConstruction=200
#
# 方法:
#   - search(collection, vector, top_k, filters) -> list[dict]
#   - insert(collection, entities) -> list[str]
#   - delete(collection, ids) -> None
#   - ensure_collections() -> None  # 启动时创建/校验Collection
# =============================================================================
