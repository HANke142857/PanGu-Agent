"""
内存仓储实现（开发 / 测试专用）。
实现 domain 层所有仓储接口，数据存于进程内 dict，重启即清空。
切换到真实 PostgreSQL 时，只需替换注入点，业务代码零改动。
"""
from __future__ import annotations
import uuid
from uuid import UUID
from idmas.domain.drawing.entities import Drawing, DrawingLabel
from idmas.domain.drawing.repository import DrawingRepository
from idmas.domain.analysis.entities import AnalysisTask, ReviewRecord
from idmas.domain.analysis.repository import AnalysisTaskRepository
from idmas.domain.analysis.value_objects import TaskStatus


class InMemoryDrawingRepository(DrawingRepository):
    def __init__(self) -> None:
        self._drawings: dict[UUID, Drawing]           = {}
        self._labels:   dict[UUID, list[DrawingLabel]] = {}   # drawing_id → labels

    async def get_by_id(self, drawing_id: UUID) -> Drawing | None:
        return self._drawings.get(drawing_id)

    async def save(self, drawing: Drawing) -> Drawing:
        self._drawings[drawing.id] = drawing
        return drawing

    async def list_by_user(self, user_id: UUID, offset: int = 0, limit: int = 20) -> list[Drawing]:
        results = [d for d in self._drawings.values() if d.created_by == user_id]
        return results[offset: offset + limit]

    async def search_by_title(self, keyword: str, limit: int = 20) -> list[Drawing]:
        kw = keyword.lower()
        return [d for d in self._drawings.values() if kw in d.title.lower()][:limit]

    async def list_all(self, offset: int = 0, limit: int = 20) -> list[Drawing]:
        ordered = sorted(self._drawings.values(), key=lambda d: d.created_at, reverse=True)
        return ordered[offset: offset + limit]

    async def count_all(self) -> int:
        return len(self._drawings)

    async def delete(self, drawing_id: UUID) -> None:
        drawing = self._drawings.get(drawing_id)
        if drawing:
            from idmas.domain.drawing.value_objects import LifecycleState
            drawing.lifecycle_state = LifecycleState.obsolete

    async def get_labels(self, drawing_id: UUID) -> list[DrawingLabel]:
        return list(self._labels.get(drawing_id, []))

    async def save_labels(self, labels: list[DrawingLabel]) -> None:
        for label in labels:
            bucket = self._labels.setdefault(label.drawing_id, [])
            # 替换同 label_id 的旧记录
            existing = next((i for i, l in enumerate(bucket) if l.label_id == label.label_id), None)
            if existing is not None:
                bucket[existing] = label
            else:
                bucket.append(label)

    async def update_label(self, label: DrawingLabel) -> None:
        await self.save_labels([label])

    # 测试辅助
    def clear(self) -> None:
        self._drawings.clear()
        self._labels.clear()

    @property
    def count(self) -> int:
        return len(self._drawings)


class InMemoryAnalysisTaskRepository(AnalysisTaskRepository):
    def __init__(self) -> None:
        self._tasks:   dict[UUID, AnalysisTask]   = {}
        self._reviews: dict[UUID, list[ReviewRecord]] = {}  # task_id → reviews

    async def get_by_id(self, task_id: UUID) -> AnalysisTask | None:
        return self._tasks.get(task_id)

    async def save(self, task: AnalysisTask) -> AnalysisTask:
        self._tasks[task.id] = task
        return task

    async def update_status(self, task_id: UUID, status: TaskStatus) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.status = status

    async def update_result(self, task_id: UUID, field: str, result: dict) -> None:
        task = self._tasks.get(task_id)
        if task and hasattr(task, field):
            setattr(task, field, result)

    async def list_by_user(
        self,
        user_id:  UUID,
        status:   TaskStatus | None = None,
        offset:   int = 0,
        limit:    int = 20,
    ) -> list[AnalysisTask]:
        results = [t for t in self._tasks.values() if t.user_id == user_id]
        if status:
            results = [t for t in results if t.status == status]
        return results[offset: offset + limit]

    async def list_all(self, offset: int = 0, limit: int = 20) -> list[AnalysisTask]:
        ordered = sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)
        return ordered[offset: offset + limit]

    async def count_all(self) -> int:
        return len(self._tasks)

    async def list_pending_reviews(self) -> list[AnalysisTask]:
        return [t for t in self._tasks.values() if t.status == TaskStatus.waiting_review]

    async def save_review(self, review: ReviewRecord) -> ReviewRecord:
        self._reviews.setdefault(review.task_id, []).append(review)
        return review

    async def get_reviews_by_task(self, task_id: UUID) -> list[ReviewRecord]:
        return list(self._reviews.get(task_id, []))

    def clear(self) -> None:
        self._tasks.clear()
        self._reviews.clear()

    @property
    def count(self) -> int:
        return len(self._tasks)
