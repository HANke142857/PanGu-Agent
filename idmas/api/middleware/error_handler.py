# =============================================================================
# 全局错误处理中间件
#
# 职责:
#   - 捕获所有未处理异常
#   - 将领域异常映射为标准错误响应
#   - 记录错误日志 (含trace_id, request_id)
#   - 敏感信息脱敏 (生产环境不暴露内部细节)
#
# 错误响应格式 (参见技术设计2.3节):
#   {
#     "error": {
#       "code": "IDMAS-503-001",
#       "message": "Vision Agent推理服务暂不可用",
#       "detail": "vLLM连接超时",       # 仅开发环境
#       "retry_after": 30,              # 可选
#       "request_id": "req_abc123"
#     }
#   }
#
# 异常→错误码映射:
#   InvalidDrawingError     → IDMAS-400-003
#   AuthenticationError     → IDMAS-401-001
#   AuthorizationError      → IDMAS-403-001
#   DrawingNotFoundError    → IDMAS-404-001
#   RateLimitExceededError  → IDMAS-429-001
#   VLLMInferenceError      → IDMAS-503-001
#   PLMConnectionError      → IDMAS-503-003
#   其他未知异常            → IDMAS-500-001
# =============================================================================
