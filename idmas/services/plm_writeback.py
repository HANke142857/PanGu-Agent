"""
PLM 回写服务（应用服务）。

把已完成任务的解析结果（标号 + 报告）组装为回写载荷，调用目标 PLM 适配器写回。
幂等由适配器基类保证；本服务只管校验状态与组装数据。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from uuid import UUID

from idmas.domain.analysis.repository import AnalysisTaskRepository
from idmas.domain.analysis.value_objects import TaskStatus
from idmas.domain.drawing.repository import DrawingRepository
from idmas.domain.shared.exceptions import InvalidTaskStateError, TaskNotFoundError
from idmas.infrastructure.adapters.base import BasePLMAdapter, PLMWriteResult

logger = logging.getLogger(__name__)

# system 名称 -> 适配器实例
PLMAdapterFactory = Callable[[str], BasePLMAdapter]


class PLMWritebackService:
    def __init__(
        self,
        task_repo: AnalysisTaskRepository,
        drawing_repo: DrawingRepository,
        adapter_factory: PLMAdapterFactory,
    ) -> None:
        self._task_repo = task_repo
        self._drawing_repo = drawing_repo
        self._factory = adapter_factory

    async def writeback(self, task_id: UUID, target_system: str) -> PLMWriteResult:
        task = await self._task_repo.get_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(str(task_id))
        if task.status != TaskStatus.completed:
            # 仅允许回写已完成（含人工审核通过）的任务
            raise InvalidTaskStateError(task.status.value, TaskStatus.completed.value)

        drawing = await self._drawing_repo.get_by_id(task.drawing_id)
        labels = await self._drawing_repo.get_labels(task.drawing_id)

        doc_id = (drawing.source_doc_id if drawing and drawing.source_doc_id else str(task.drawing_id))
        data = {
            "task_id":       str(task.id),
            "drawing_id":    str(task.drawing_id),
            "labels": [
                {"label_id": lbl.label_id, "name": lbl.name, "confidence": lbl.confidence.value}
                for lbl in labels
            ],
            "report":        task.report_result,
            "model_version": task.model_version,
        }

        adapter = self._factory(target_system)
        result = await adapter.writeback(doc_id, data)
        logger.info(
            "[plm] writeback task=%s system=%s success=%s skipped=%s",
            task_id, target_system, result.success, result.skipped,
        )
        return result
