"""
任务消费循环装配。

run_worker() 按配置组装：RabbitMQ 队列 + SQL 仓储 + LLM 客户端 + TaskProcessor，
然后阻塞消费 task.created 队列。供 idmas.worker 入口调用。
"""

from __future__ import annotations

import logging

from idmas.config.settings import get_settings
from idmas.infrastructure.db.repositories import (
    SQLAnalysisTaskRepository,
    SQLDrawingRepository,
)
from idmas.infrastructure.db.session import close_db, get_session_factory, init_db
from idmas.infrastructure.llm.vllm_client import FakeVLLMClient, VLLMClient
from idmas.infrastructure.mq.publisher import RabbitMQTaskQueue
from idmas.services.task_processor import TaskProcessor

logger = logging.getLogger(__name__)


def _build_llm_client():
    """生产用真实 vLLM，开发回落到 Fake。"""
    settings = get_settings()
    if settings.is_development:
        logger.warning("Worker 使用 FakeVLLMClient（开发环境）")
        return FakeVLLMClient()
    return VLLMClient(settings)


async def run_worker() -> None:
    settings = get_settings()

    await init_db()
    factory = get_session_factory()
    drawing_repo = SQLDrawingRepository(factory)
    task_repo = SQLAnalysisTaskRepository(factory)
    processor = TaskProcessor(drawing_repo, task_repo, _build_llm_client())

    queue = RabbitMQTaskQueue(settings.RABBITMQ_URL)
    logger.info("Worker 启动，开始消费 task.created")
    try:
        await queue.consume(processor.handle)
    finally:
        await queue.close()
        await close_db()
