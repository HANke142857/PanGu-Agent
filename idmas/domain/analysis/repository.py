"""
解析任务仓储接口（Repository Interface）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from idmas.domain.analysis.entities import AnalysisTask, ReviewRecord
from idmas.domain.analysis.value_objects import TaskStatus


class AnalysisTaskRepository(ABC):
    """解析任务仓储抽象接口。"""

    @abstractmethod
    async def get_by_id(self, task_id: UUID) -> AnalysisTask | None:
        ...

    @abstractmethod
    async def save(self, task: AnalysisTask) -> AnalysisTask:
        ...

    @abstractmethod
    async def update_status(self, task_id: UUID, status: TaskStatus) -> None:
        ...

    @abstractmethod
    async def update_result(self, task_id: UUID, field: str, result: dict) -> None:
        """更新单个 Agent 的输出字段，如 vision_result / report_result。"""
        ...

    @abstractmethod
    async def list_by_user(
        self,
        user_id:  UUID,
        status:   TaskStatus | None = None,
        offset:   int               = 0,
        limit:    int               = 20,
    ) -> list[AnalysisTask]:
        ...

    @abstractmethod
    async def list_all(self, offset: int = 0, limit: int = 20) -> list[AnalysisTask]:
        """分页查询全部任务（不限用户），按创建时间倒序。"""
        ...

    @abstractmethod
    async def count_all(self) -> int:
        """统计任务总数（用于分页 total）。"""
        ...

    @abstractmethod
    async def list_pending_reviews(self) -> list[AnalysisTask]:
        """获取所有 waiting_review 状态的任务（人工审核队列）。"""
        ...

    @abstractmethod
    async def save_review(self, review: ReviewRecord) -> ReviewRecord:
        ...

    @abstractmethod
    async def get_reviews_by_task(self, task_id: UUID) -> list[ReviewRecord]:
        ...
