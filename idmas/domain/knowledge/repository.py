# =============================================================================
# 知识库仓储接口 (Knowledge Repository Interface)
#
# 接口方法:
#   - search_by_vector(embedding: list[float], top_k: int) -> list[KnowledgeDocument]
#   - search_by_keyword(query: str, top_k: int) -> list[KnowledgeDocument]
#   - get_part_by_name(name: str) -> Part | None
#   - get_equipment_relations(part_id: UUID) -> list[Equipment]
#   - get_fault_records(equipment_id: UUID) -> list[FaultRecord]
#   - save_document(doc: KnowledgeDocument) -> KnowledgeDocument
# =============================================================================
