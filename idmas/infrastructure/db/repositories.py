# =============================================================================
# 仓储实现 (Repository Implementations)
#
# 实现 domain 层定义的仓储接口
# 使用 SQLAlchemy AsyncSession 进行数据库操作
#
# 实现类:
#   - SQLDrawingRepository: 实现 DrawingRepository 接口
#   - SQLAnalysisTaskRepository: 实现 AnalysisTaskRepository 接口
#   - SQLKnowledgeRepository: 实现 KnowledgeRepository 接口 (部分，图谱部分由Neo4j实现)
#   - SQLAuditLogRepository: 审计日志仓储
#
# 原则:
#   - 所有查询使用参数化 (防SQL注入)
#   - 批量操作使用 bulk_insert_mappings
#   - 合理使用索引和分页
# =============================================================================
