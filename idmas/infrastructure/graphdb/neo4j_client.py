# =============================================================================
# Neo4j 图数据库客户端
#
# 职责:
#   - 管理Neo4j连接 (async driver)
#   - 知识图谱CRUD操作
#
# 配置:
#   - NEO4J_URI: 连接地址 (bolt://localhost:7687)
#   - NEO4J_USER / NEO4J_PASSWORD: 认证
#
# 图谱模型 (参见技术设计3.4节):
#   节点: Drawing, Label, Part, Equipment, FaultRecord
#   关系: HAS_LABEL, REFERS_TO, INSTALLED_IN, HAS_FAULT, SAME_AS, VERSION_OF
#
# 方法:
#   - create_label_node(label: dict) -> str
#   - create_part_node(part: dict) -> str
#   - create_relation(from_id, to_id, rel_type, props) -> None
#   - query_label_relations(label_name: str) -> dict
#     查询: Label → Part → Equipment → FaultRecord 关系链
#   - query_cross_drawing_labels(label_name: str) -> list[dict]
#     查询: 跨图标号关联 (SAME_AS关系)
#   - health_check() -> bool
#
# 降级策略: Neo4j不可用时，图谱功能跳过，不影响核心解析
# =============================================================================
