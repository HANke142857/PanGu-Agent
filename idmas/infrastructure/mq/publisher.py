"""
RabbitMQ 任务队列实现（生产）。

基于 aio-pika，实现 BaseTaskQueue。aio-pika 惰性导入——仅在实例化本类时
才需要安装，测试用 EagerTaskQueue 不受影响。

Queue 约定（参见技术设计 6.2）::

    task.created     FastAPI → Worker（新任务分发，本类负责）
    task.completed   Worker  → 通知服务（后续接入）
    plm.writeback    审核服务 → PLM 适配器（后续接入）

可靠性：
  - 发布持久化消息（delivery_mode=PERSISTENT）
  - 消费手动 ACK，handler 异常则 NACK 不重回队列（避免毒消息打爆 Worker；
    后续接 DLQ）
"""

from __future__ import annotations

import logging

from idmas.infrastructure.mq.base import BaseTaskQueue, TaskHandler, TaskMessage

logger = logging.getLogger(__name__)

QUEUE_TASK_CREATED = "task.created"


class RabbitMQTaskQueue(BaseTaskQueue):
    """RabbitMQ 实现的任务队列。"""

    def __init__(self, url: str, queue_name: str = QUEUE_TASK_CREATED) -> None:
        self._url = url
        self._queue_name = queue_name
        self._connection = None
        self._channel = None

    async def _ensure_channel(self):
        """惰性建立连接与信道。"""
        if self._channel is not None:
            return self._channel
        import aio_pika  # 惰性导入

        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=1)
        await self._channel.declare_queue(self._queue_name, durable=True)
        return self._channel

    async def publish(self, message: TaskMessage) -> None:
        import aio_pika  # 惰性导入

        channel = await self._ensure_channel()
        body = message.model_dump_json().encode("utf-8")
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            ),
            routing_key=self._queue_name,
        )
        logger.info("published %s task_id=%s", message.message_type, message.task_id)

    async def consume(self, handler: TaskHandler) -> None:
        channel = await self._ensure_channel()
        queue = await channel.declare_queue(self._queue_name, durable=True)
        logger.info("consuming queue=%s", self._queue_name)

        async with queue.iterator() as it:
            async for raw in it:
                try:
                    message = TaskMessage.model_validate_json(raw.body.decode("utf-8"))
                    await handler(message)
                    await raw.ack()
                except Exception:  # noqa: BLE001
                    logger.exception("消息处理失败，NACK 丢弃（后续接 DLQ）")
                    await raw.nack(requeue=False)

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
        self._connection = None
        self._channel = None
