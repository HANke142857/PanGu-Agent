# =============================================================================
# 健康检查路由
#
# 端点:
#   GET /api/v1/health              基础健康检查 (无限流)
#     - 返回服务状态、版本号
#
#   GET /api/v1/health/ready        就绪检查 (K8s readinessProbe)
#     - 检查所有依赖服务连通性:
#       PostgreSQL / Redis / vLLM / RabbitMQ / Milvus / Neo4j / ES / MinIO
#     - 全部通过返回200，任一失败返回503
#
#   GET /api/v1/health/live         存活检查 (K8s livenessProbe)
#     - 轻量检查，仅确认进程存活
# =============================================================================
