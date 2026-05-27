# =============================================================================
# 解析任务路由 (参见技术设计2.2节 API契约)
#
# 端点:
#   POST /api/v1/tasks              创建解析任务 (限流: 10/min)
#     - 接收图纸ID、提问、Prompt模式等参数
#     - 发布task.created消息到RabbitMQ
#     - 返回202 Accepted + task_id
#
#   GET  /api/v1/tasks/{id}         查询任务结果 (限流: 60/min)
#     - 返回任务状态和各Agent结果
#
#   GET  /api/v1/tasks/{id}/stream  SSE流式进度 (限流: 10/min)
#     - 订阅Redis Pub/Sub通道 (sse:task:{task_id})
#     - 推送事件: intent/vision/ocr/conflict/review/done/error
#
#   POST /api/v1/tasks/{id}/review  提交审核结果 (限流: 30/min)
#     - 工程师提交标号修正/确认
#     - 恢复LangGraph (resume from interrupt)
#
#   POST /api/v1/tasks/batch        批量任务 (限流: 2/min)
#     - 批量创建多个解析任务
# =============================================================================
