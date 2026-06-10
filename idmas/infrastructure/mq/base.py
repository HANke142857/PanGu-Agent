"""
任务队列抽象。

设计与 LLM 客户端一致（依赖倒置 + 可替换实现）::

    BaseTaskQueue   : 抽象接口，调用方只依赖它
    EagerTaskQueue  : 测试/开发用，发布即就地处理（无需 RabbitMQ）
    RabbitMQTaskQueue: 生产实现，见 publisher.py（需 RabbitMQ）

消息流（参见技术设计 6.2）::

    FastAPI  --task.created-->  [queue]  -->  LangGraph Worker

API 只负责创建任务并 publish，真正的解析在 Worker 侧消费后执行。
EagerTaskQueue 把"消费"折叠进 publish，使单机/测试无需独立 Worker。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from uuid import UUID

from pydantic import BaseModel, Field

# 任务处理回调签名：接收一条消息，异步处理，无返回。
TaskHandler = Callable[["TaskMessage"], Awaitable[None]]


class TaskMessage(BaseModel):
    """队列中流转的任务消息。仅携带 ID 与少量路由信息，正文从仓储读取。"""

    task_id:      UUID
    drawing_id:   UUID
    message_type: str            = "task.created"
    payload:      dict           = Field(default_factory=dict)


class BaseTaskQueue(ABC):
    """任务队列抽象接口。"""

    @abstractmethod
    async def publish(self, message: TaskMessage) -> None:
        """发布一条任务消息。"""
        ...

    @abstractmethod
    async def consume(self, handler: TaskHandler) -> None:
        """持续消费消息并交给 handler 处理（阻塞，直到取消）。"""
        ...

    async def close(self) -> None:
        """释放连接等资源。默认无操作。"""
        return None


class EagerTaskQueue(BaseTaskQueue):
    """
    进程内"急切"队列：publish 时立即调用 handler 处理。

    用于单机部署与测试——保持"POST 任务后即可拿到结果"的同步语义，
    无需启动独立 Worker，也无需 RabbitMQ。
    """

    def __init__(self, handler: TaskHandler | None = None) -> None:
        self._handler = handler
        self.published: list[TaskMessage] = []   # 便于测试断言

    def set_handler(self, handler: TaskHandler) -> None:
        self._handler = handler

    async def publish(self, message: TaskMessage) -> None:
        self.published.append(message)
        if self._handler is not None:
            await self._handler(message)

    async def consume(self, handler: TaskHandler) -> None:
        # Eager 模式无独立消费循环；保留接口以满足契约。
        self._handler = handler
