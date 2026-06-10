"""
解析任务处理器（应用服务）。

把"运行 Master Graph → 回写结果 → 推进任务状态"的用例逻辑从 API 路由抽出，
使其可被两个入口复用：

  - EagerTaskQueue（单机/测试）：API publish 时就地调用
  - Worker（生产）：消费 RabbitMQ task.created 队列时调用

处理器只依赖 domain 仓储接口与 LLM 客户端抽象，便于注入 Fake 实现测试。
"""

from __future__ import annotations

import logging
import time
from uuid import UUID

from idmas.domain.analysis.repository import AnalysisTaskRepository
from idmas.domain.drawing.repository import DrawingRepository
from idmas.domain.drawing.entities import DrawingLabel, LabelSource
from idmas.domain.drawing.value_objects import BoundingBox, SpatialInfo
from idmas.domain.shared.value_objects import Confidence
from idmas.infrastructure.llm.vllm_client import BaseLLMClient
from idmas.infrastructure.mq.base import TaskMessage

logger = logging.getLogger(__name__)


class TaskProcessor:
    """驱动单个解析任务从 created 跑到终态。"""

    def __init__(
        self,
        drawing_repo: DrawingRepository,
        task_repo: AnalysisTaskRepository,
        llm_client: BaseLLMClient,
        *,
        enable_human_review: bool = True,
        metrics=None,
    ) -> None:
        self._drawing_repo = drawing_repo
        self._task_repo = task_repo
        self._llm = llm_client
        self._enable_human_review = enable_human_review
        if metrics is None:
            from idmas.infrastructure.observability.metrics import NoopMetrics
            metrics = NoopMetrics()
        self._metrics = metrics

    async def handle(self, message: TaskMessage) -> None:
        """队列回调入口。"""
        await self.process(message.task_id)

    async def process(self, task_id: UUID) -> None:
        """
        执行一个解析任务。幂等性由调用方/状态机保证；此方法不抛异常，
        失败统一落到 task.error_*，避免 Worker 因单条消息崩溃。
        """
        task = await self._task_repo.get_by_id(task_id)
        if task is None:
            logger.warning("TaskProcessor: task %s 不存在，跳过", task_id)
            return

        drawing = await self._drawing_repo.get_by_id(task.drawing_id)
        if drawing is None:
            task.mark_failed("IDMAS-404-001", f"Drawing {task.drawing_id} not found")
            await self._task_repo.save(task)
            return

        thread_id = f"thread-{task_id}"
        task.mark_processing(thread_id)
        await self._task_repo.save(task)

        t0 = time.monotonic()
        try:
            from idmas.agents.master.graph import build_master_graph

            graph, _ = await build_master_graph(
                llm_client=self._llm,
                enable_human_review=self._enable_human_review,
            )
            result = await graph.ainvoke(
                {
                    "image_url":   drawing.file_url,
                    "prompt_mode": task.prompt_mode.value,
                    "task_type":   task.task_type.value,
                    "user_query":  task.question,
                    "request_id":  str(task_id),
                    "messages":    [],
                },
                config={"configurable": {"thread_id": thread_id}},
            )

            elapsed_ms = int((time.monotonic() - t0) * 1000)
            await self._writeback(task, drawing.id, result, elapsed_ms)
        except Exception as exc:  # noqa: BLE001 — 顶层兜底，错误入库
            logger.exception("TaskProcessor: task %s 处理失败", task_id)
            task.mark_failed("IDMAS-502-002", str(exc))

        await self._task_repo.save(task)

        # ── 指标 ──
        self._metrics.observe_agent("master", time.monotonic() - t0)
        self._metrics.inc_task(task.status.value)
        self._metrics.inc_tokens(task.total_tokens)
        if task.conflicts:
            self._metrics.inc_conflict(len(task.conflicts))

    # ------------------------------------------------------------------
    # 内部：结果回写
    # ------------------------------------------------------------------

    async def _writeback(self, task, drawing_id, result: dict, elapsed_ms: int) -> None:
        vision_final = result.get("vision_result") or {}
        task.vision_result    = vision_final
        task.design_result    = result.get("design_result") or {}
        task.process_result   = result.get("process_result") or {}
        task.knowledge_result = result.get("knowledge_result") or {}
        task.report_result    = result.get("report_result") or {}

        if vision_final.get("success") or vision_final.get("labels"):
            raw_labels = vision_final.get("labels", [])
            new_labels = [self._build_label(drawing_id, raw) for raw in raw_labels]
            await self._drawing_repo.save_labels(new_labels)

            needs_review = self._enable_human_review and any(
                raw.get("needs_review") for raw in raw_labels
            )
            if needs_review:
                task.mark_waiting_review()
            else:
                task.mark_completed(elapsed_ms, total_tokens=0)
            return

        master_status = result.get("status", "")
        if master_status == "waiting_review":
            task.mark_waiting_review()
        elif master_status == "failed":
            task.mark_failed("IDMAS-502-002", result.get("error") or "Master Agent failed")
        else:
            task.mark_failed("IDMAS-502-002", "Vision Agent returned no labels")

    @staticmethod
    def _build_label(drawing_id: UUID, raw: dict) -> DrawingLabel:
        bb_data = raw.get("bounding_box", {})
        try:
            bbox = BoundingBox(**bb_data)
            spatial = SpatialInfo.from_bounding_box(bbox, raw.get("spatial_description", ""))
        except Exception:  # noqa: BLE001 — 坐标缺失时给安全默认
            bbox = BoundingBox(x=0.0, y=0.0, width=0.1, height=0.1)
            spatial = SpatialInfo.from_bounding_box(bbox)

        return DrawingLabel(
            drawing_id=drawing_id,
            label_id=str(raw.get("label_id", "")),
            name=str(raw.get("name", "")),
            confidence=Confidence(value=float(raw.get("confidence", 0.0))),
            bounding_box=bbox,
            spatial_info=spatial,
            source=LabelSource.VISION_AGENT,
        )
