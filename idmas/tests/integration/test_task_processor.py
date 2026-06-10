"""
TaskProcessor 集成测试。

用内存仓储 + FakeVLLMClient 驱动真实 Master Graph，验证：
  - process() 推进任务 created → 终态，并回写 vision_result / 标号
  - 图纸缺失 → 任务失败
  - 异步解耦：rabbitmq 风格队列 publish 后任务仍为 created，
    交给 processor（模拟 Worker）后才进入终态
"""

from __future__ import annotations

import uuid

import pytest

from idmas.domain.analysis.entities import AnalysisTask
from idmas.domain.analysis.value_objects import TaskStatus
from idmas.domain.drawing.entities import Drawing
from idmas.domain.drawing.value_objects import DrawingType, FileFormat
from idmas.infrastructure.db.memory_repositories import (
    InMemoryAnalysisTaskRepository,
    InMemoryDrawingRepository,
)
from idmas.infrastructure.llm.vllm_client import FakeVLLMClient
from idmas.infrastructure.mq.base import BaseTaskQueue, TaskMessage
from idmas.services.task_processor import TaskProcessor

_TERMINAL = {TaskStatus.completed, TaskStatus.waiting_review, TaskStatus.failed}


@pytest.fixture()
def drawing_repo():
    return InMemoryDrawingRepository()


@pytest.fixture()
def task_repo():
    return InMemoryAnalysisTaskRepository()


@pytest.fixture()
def processor(drawing_repo, task_repo):
    return TaskProcessor(drawing_repo, task_repo, FakeVLLMClient())


async def _seed_drawing(drawing_repo) -> Drawing:
    d = Drawing(
        title="齿轮箱装配图",
        drawing_type=DrawingType.assembly,
        file_format=FileFormat.png,
        file_url="http://minio/x.png",
        created_by=uuid.uuid4(),
    )
    await drawing_repo.save(d)
    return d


async def _seed_task(task_repo, drawing_id) -> AnalysisTask:
    t = AnalysisTask(drawing_id=drawing_id, user_id=uuid.uuid4())
    await task_repo.save(t)
    return t


class TestProcess:
    async def test_process_reaches_terminal_and_writes_results(
        self, processor, drawing_repo, task_repo
    ):
        d = await _seed_drawing(drawing_repo)
        t = await _seed_task(task_repo, d.id)
        assert t.status is TaskStatus.created

        await processor.process(t.id)

        done = await task_repo.get_by_id(t.id)
        assert done.status in _TERMINAL
        # FakeVLLM 默认含低置信度标号 → 进入人工审核
        assert done.status is TaskStatus.waiting_review
        assert done.vision_result  # 已回写
        labels = await drawing_repo.get_labels(d.id)
        assert len(labels) == 3

    async def test_process_via_handle_message(self, processor, drawing_repo, task_repo):
        d = await _seed_drawing(drawing_repo)
        t = await _seed_task(task_repo, d.id)
        await processor.handle(TaskMessage(task_id=t.id, drawing_id=d.id))
        done = await task_repo.get_by_id(t.id)
        assert done.status in _TERMINAL

    async def test_missing_drawing_marks_failed(self, processor, task_repo):
        t = AnalysisTask(drawing_id=uuid.uuid4(), user_id=uuid.uuid4())
        await task_repo.save(t)
        await processor.process(t.id)
        done = await task_repo.get_by_id(t.id)
        assert done.status is TaskStatus.failed
        assert done.error_code == "IDMAS-404-001"

    async def test_unknown_task_is_noop(self, processor):
        await processor.process(uuid.uuid4())  # 不应抛异常

    async def test_no_human_review_completes(self, drawing_repo, task_repo):
        proc = TaskProcessor(
            drawing_repo, task_repo, FakeVLLMClient(), enable_human_review=False
        )
        d = await _seed_drawing(drawing_repo)
        t = await _seed_task(task_repo, d.id)
        await proc.process(t.id)
        done = await task_repo.get_by_id(t.id)
        # 关闭人工审核后，低置信度也不拦截 → 直接完成
        assert done.status is TaskStatus.completed


class _CollectingQueue(BaseTaskQueue):
    """模拟 rabbitmq：publish 仅入队，不处理。"""

    def __init__(self):
        self.messages: list[TaskMessage] = []

    async def publish(self, message: TaskMessage) -> None:
        self.messages.append(message)

    async def consume(self, handler) -> None:  # noqa: ANN001
        for m in list(self.messages):
            await handler(m)


class TestAsyncDecoupling:
    async def test_publish_then_worker_consume(self, processor, drawing_repo, task_repo):
        d = await _seed_drawing(drawing_repo)
        t = await _seed_task(task_repo, d.id)

        queue = _CollectingQueue()
        await queue.publish(TaskMessage(task_id=t.id, drawing_id=d.id))

        # 发布后任务仍未处理（异步语义）
        assert (await task_repo.get_by_id(t.id)).status is TaskStatus.created

        # Worker 消费 → 处理器推进到终态
        await queue.consume(processor.handle)
        assert (await task_repo.get_by_id(t.id)).status in _TERMINAL
