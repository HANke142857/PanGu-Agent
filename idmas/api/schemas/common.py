# =============================================================================
# 通用 Pydantic Schema
#
# 包含:
#   - ErrorResponse: 统一错误响应
#     - error.code: str (如 "IDMAS-503-001")
#     - error.message: str
#     - error.detail: str | None (仅开发环境)
#     - error.retry_after: int | None
#     - error.request_id: str
#
#   - PaginationParams: 分页参数
#     - offset: int (默认0)
#     - limit: int (默认20, 最大100)
#
#   - PaginatedResponse: 分页响应包装
#     - items: list
#     - total: int
#     - offset: int
#     - limit: int
#
#   - HealthResponse: 健康检查响应
#     - status: str (healthy/unhealthy)
#     - version: str
#     - dependencies: dict[str, str]  # 各依赖服务状态
# =============================================================================
