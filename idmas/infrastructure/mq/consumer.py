# =============================================================================
# RabbitMQ 消息消费者
#
# 职责:
#   - 消费Queue中的任务消息并调用对应处理器
#   - 消息ACK/NACK管理
#   - 死信队列(DLQ)处理
#
# 消费者:
#   - TaskCreatedConsumer: 消费task.created → 启动LangGraph执行
#   - PLMWritebackConsumer: 消费plm.writeback → 调用PLM适配器回写
#
# 死信队列:
#   - plm.writeback.dlq: PLM回写5次重试全部失败的消息
#     触发告警(Alertmanager)，运维人工处理
#
# 方法:
#   - start_consuming(queue_name, handler) -> None
#   - stop() -> None
# =============================================================================
