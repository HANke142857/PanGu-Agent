# =============================================================================
# Token计数器
#
# 包含:
#   - TokenCounter: Token使用统计
#     - count_tokens(text: str, model: str) -> int
#     - track_usage(request_id: str, model: str, input_tokens: int, output_tokens: int)
#     - get_total_usage(request_id: str) -> dict
#
#   - 统计维度:
#     - 按请求ID累计
#     - 按Agent类型统计
#     - 按模型版本统计
#
#   - 用途:
#     - 成本核算
#     - Prometheus指标上报
#     - 持久化到analysis_tasks.total_tokens
# =============================================================================
