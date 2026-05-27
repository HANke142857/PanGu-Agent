# =============================================================================
# Prometheus 指标采集
#
# 职责:
#   - 定义并导出Prometheus自定义指标
#   - 暴露 /metrics 端点
#
# 黄金指标 (参见技术设计7.7节):
#   - idmas_request_duration_seconds (Histogram): API请求延迟
#   - idmas_request_total (Counter): 请求总数 (按路径/状态码)
#   - idmas_error_total (Counter): 错误总数 (按错误码)
#   - idmas_agent_duration_seconds (Histogram): Agent执行时间 (按Agent类型)
#   - idmas_vllm_inference_seconds (Histogram): vLLM推理耗时
#   - idmas_task_queue_size (Gauge): 任务队列积压数
#   - idmas_active_tasks (Gauge): 活跃任务数
#   - idmas_tokens_total (Counter): Token消耗总量
#   - idmas_conflict_total (Counter): 冲突触发次数
#   - idmas_human_review_queue_size (Gauge): 人工审核队列长度
#
# 告警阈值:
#   - P99延迟 > 10s → 企业微信
#   - 错误率 > 5% → 企业微信+电话
#   - GPU利用率 > 95% 持续5min → 企业微信
#   - 队列积压 > 50 → 企业微信
# =============================================================================
