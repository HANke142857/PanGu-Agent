# =============================================================================
# API限流中间件
#
# 基于 SlowAPI + Redis后端 实现
#
# 限流规则 (参见技术设计5.5节):
#   /api/v1/tasks:          10/minute
#   /api/v1/tasks/batch:    2/minute
#   /api/v1/knowledge:      30/minute
#   global_per_user:        100/minute
#
# vLLM层限流:
#   max_concurrent: 8       # 5090单卡上限
#   max_queue: 50           # 排队上限
#   request_timeout: 60     # 单次超时
#
# 超限响应:
#   HTTP 429 + Retry-After header
#   错误码: IDMAS-429-001
# =============================================================================
