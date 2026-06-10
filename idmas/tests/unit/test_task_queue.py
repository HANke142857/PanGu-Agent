"""
任务队列单元测试。

覆盖：
  - TaskMessage 序列化往返
  - EagerTaskQueue 发布即处理 / 无 handler 仅记录
  - RabbitMQTaskQueue.publish 构造持久化消息（用 Fake channel，无需真实 broker）
"""

from __future__ import annotations

import uuid

import pytest

from idmas.infrastructure.mq.base import EagerTaskQueue, TaskMessage
from idmas.infrastructure.mq.publisher import QUEUE_TASK_CREATED, RabbitMQTaskQueue


def test_task_message_json_roundtrip():
    msg = TaskMessage(task_id=uuid.uuid4(), drawing_id=uuid.uuid4())
    restored = TaskMessage.model_validate_json(msg.model_dump_json())
    assert restored == msg
    assert restored.message_type == "task.created"


class TestEagerTaskQueue:
    async def test_publish_invokes_handler(self):
        seen: list[TaskMessage] = []

        async def handler(m: TaskMessage) -> None:
            seen.append(m)

        q = EagerTaskQueue(handler=handler)
        msg = TaskMessage(task_id=uuid.uuid4(), drawing_id=uuid.uuid4())
        await q.publish(msg)

        assert seen == [msg]
        assert q.published == [msg]      # 同时记录，便于断言

    async def test_publish_without_handler_only_records(self):
        q = EagerTaskQueue()
        msg = TaskMessage(task_id=uuid.uuid4(), drawing_id=uuid.uuid4())
        await q.publish(msg)             # 不应抛异常
        assert q.published == [msg]

    async def test_set_handler_late_binding(self):
        seen: list[TaskMessage] = []
        q = EagerTaskQueue()
        q.set_handler(lambda m: _append(seen, m))
        msg = TaskMessage(task_id=uuid.uuid4(), drawing_id=uuid.uuid4())
        await q.publish(msg)
        assert seen == [msg]


async def _append(bucket, m):
    bucket.append(m)


class _FakeExchange:
    def __init__(self):
        self.published: list = []

    async def publish(self, message, routing_key):  # noqa: ANN001
        self.published.append((message, routing_key))


class _FakeChannel:
    def __init__(self):
        self.default_exchange = _FakeExchange()


class TestRabbitMQTaskQueuePublish:
    async def test_publish_builds_persistent_message(self, monkeypatch):
        import aio_pika

        q = RabbitMQTaskQueue("amqp://unused")
        fake_channel = _FakeChannel()

        async def fake_ensure():
            return fake_channel

        monkeypatch.setattr(q, "_ensure_channel", fake_ensure)

        msg = TaskMessage(task_id=uuid.uuid4(), drawing_id=uuid.uuid4())
        await q.publish(msg)

        assert len(fake_channel.default_exchange.published) == 1
        published_msg, routing_key = fake_channel.default_exchange.published[0]
        assert routing_key == QUEUE_TASK_CREATED
        assert published_msg.delivery_mode == aio_pika.DeliveryMode.PERSISTENT
        # body 可反序列化回原消息
        assert TaskMessage.model_validate_json(published_msg.body.decode()) == msg
