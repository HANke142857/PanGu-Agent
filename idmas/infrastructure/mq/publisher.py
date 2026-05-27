# =============================================================================
# RabbitMQ 消息发布者
#
# 职责:
#   - 发布任务消息到指定Queue
#
# Queue定义 (参见技术设计6.2节):
#   - task.created:        FastAPI → LangGraph Worker (新任务分发)
#   - task.completed:      LangGraph → Notification Service (完成通知)
#   - plm.writeback:       Review Service → PLM Adapter (回写请求)
#   - data.feedback:       Review Service → Training Pipeline (修正数据回流)
#
# 方法:
#   - publish(queue_name, message, headers) -> None
#   - publish_task_created(task_id, drawing_id, user_id) -> None
#   - publish_task_completed(task_id, result_summary) -> None
#   - publish_plm_writeback(task_id, target_system, data) -> None
#   - publish_data_feedback(review_record) -> None
# =============================================================================
