# =============================================================================
# LangChain 回调处理器
#
# 包含:
#   - SSECallbackHandler: SSE流式输出回调
#     将Agent执行事件推送到Redis Pub/Sub通道 (sse:task:{task_id})
#     事件类型: intent/vision/ocr/conflict/review/done/error
#
#   - LangFuseCallbackHandler: LangFuse可观测性回调
#     记录每个节点的输入/输出/耗时/Token消耗
#
#   - AuditCallbackHandler: 审计回调
#     关键操作记录到审计日志表
#
#   - MetricsCallbackHandler: Prometheus指标回调
#     记录各Agent执行时间、成功/失败率
# =============================================================================
