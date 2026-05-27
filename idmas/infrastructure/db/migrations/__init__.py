# =============================================================================
# Alembic 数据库迁移
#
# 迁移策略 (参见技术设计3.7节):
#   - 每次Schema变更生成版本化迁移脚本
#   - 零停机迁移: expand-contract模式
#   - 回滚: 每个迁移必须有reverse (Alembic downgrade)
#   - 大表DDL: pg_repack / CREATE INDEX CONCURRENTLY
#   - 数据回填: 批量1000条 + sleep，避免峰值IO
#
# 命令:
#   alembic init migrations        # 初始化
#   alembic revision --autogenerate -m "描述"  # 生成迁移
#   alembic upgrade head           # 升级到最新
#   alembic downgrade -1           # 回退一个版本
# =============================================================================
