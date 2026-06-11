"""
仓储实现（PostgreSQL / SQLAlchemy Async）。

实现 domain 层定义的仓储接口，与 InMemory* 实现完全可互换：
  - SQLDrawingRepository      → DrawingRepository
  - SQLAnalysisTaskRepository → AnalysisTaskRepository

约定：
  - 仓储持有 async_sessionmaker，每个方法开一个短事务（async with ... 自动提交/回滚）。
  - ORM ↔ domain 转换全部委托 mappers，本模块只管查询与事务。
  - 所有查询参数化，分页通过 offset/limit。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from idmas.domain.analysis.entities import AnalysisTask, ReviewRecord
from idmas.domain.analysis.repository import AnalysisTaskRepository
from idmas.domain.analysis.value_objects import TaskStatus
from idmas.domain.drawing.entities import Drawing, DrawingLabel
from idmas.domain.drawing.repository import DrawingRepository
from idmas.domain.drawing.value_objects import LifecycleState
from idmas.infrastructure.db import mappers
from idmas.infrastructure.db.models import (
    AnalysisTaskModel,
    DrawingLabelModel,
    DrawingModel,
    ReviewRecordModel,
)


class SQLDrawingRepository(DrawingRepository):
    """基于 SQLAlchemy 的图纸仓储。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def get_by_id(self, drawing_id: UUID) -> Drawing | None:
        async with self._sf() as s:
            orm = await s.get(DrawingModel, drawing_id)
            return mappers.drawing_to_domain(orm) if orm else None

    async def save(self, drawing: Drawing) -> Drawing:
        async with self._sf() as s:
            existing = await s.get(DrawingModel, drawing.id)
            orm = mappers.drawing_to_orm(drawing, existing)
            if existing is None:
                s.add(orm)
            await s.commit()
            return drawing

    async def list_by_user(self, user_id: UUID, offset: int = 0, limit: int = 20) -> list[Drawing]:
        async with self._sf() as s:
            stmt = (
                select(DrawingModel)
                .where(DrawingModel.created_by == user_id)
                .order_by(DrawingModel.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            rows = (await s.execute(stmt)).scalars().all()
            return [mappers.drawing_to_domain(r) for r in rows]

    async def search_by_title(self, keyword: str, limit: int = 20) -> list[Drawing]:
        async with self._sf() as s:
            stmt = (
                select(DrawingModel)
                .where(DrawingModel.title.ilike(f"%{keyword}%"))
                .limit(limit)
            )
            rows = (await s.execute(stmt)).scalars().all()
            return [mappers.drawing_to_domain(r) for r in rows]

    async def list_all(self, offset: int = 0, limit: int = 20) -> list[Drawing]:
        async with self._sf() as s:
            stmt = (
                select(DrawingModel)
                .order_by(DrawingModel.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            rows = (await s.execute(stmt)).scalars().all()
            return [mappers.drawing_to_domain(r) for r in rows]

    async def count_all(self) -> int:
        async with self._sf() as s:
            stmt = select(func.count()).select_from(DrawingModel)
            return int((await s.execute(stmt)).scalar_one())

    async def delete(self, drawing_id: UUID) -> None:
        """逻辑删除：lifecycle_state → obsolete。"""
        async with self._sf() as s:
            orm = await s.get(DrawingModel, drawing_id)
            if orm:
                orm.lifecycle_state = LifecycleState.obsolete.value
                await s.commit()

    # -- 标号 ---------------------------------------------------------------

    async def get_labels(self, drawing_id: UUID) -> list[DrawingLabel]:
        async with self._sf() as s:
            stmt = select(DrawingLabelModel).where(DrawingLabelModel.drawing_id == drawing_id)
            rows = (await s.execute(stmt)).scalars().all()
            return [mappers.label_to_domain(r) for r in rows]

    async def save_labels(self, labels: list[DrawingLabel]) -> None:
        if not labels:
            return
        async with self._sf() as s:
            for label in labels:
                existing = await s.get(DrawingLabelModel, label.id)
                orm = mappers.label_to_orm(label, existing)
                if existing is None:
                    s.add(orm)
            await s.commit()

    async def update_label(self, label: DrawingLabel) -> None:
        await self.save_labels([label])


class SQLAnalysisTaskRepository(AnalysisTaskRepository):
    """基于 SQLAlchemy 的解析任务仓储。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def get_by_id(self, task_id: UUID) -> AnalysisTask | None:
        async with self._sf() as s:
            orm = await s.get(AnalysisTaskModel, task_id)
            return mappers.task_to_domain(orm) if orm else None

    async def save(self, task: AnalysisTask) -> AnalysisTask:
        async with self._sf() as s:
            existing = await s.get(AnalysisTaskModel, task.id)
            orm = mappers.task_to_orm(task, existing)
            if existing is None:
                s.add(orm)
            await s.commit()
            return task

    async def update_status(self, task_id: UUID, status: TaskStatus) -> None:
        async with self._sf() as s:
            orm = await s.get(AnalysisTaskModel, task_id)
            if orm:
                orm.status = status.value
                await s.commit()

    async def update_result(self, task_id: UUID, field: str, result: dict) -> None:
        """更新单个 Agent 输出字段（vision_result / report_result 等）。"""
        async with self._sf() as s:
            orm = await s.get(AnalysisTaskModel, task_id)
            if orm and hasattr(orm, field):
                setattr(orm, field, result)
                await s.commit()

    async def list_by_user(
        self,
        user_id: UUID,
        status: TaskStatus | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[AnalysisTask]:
        async with self._sf() as s:
            stmt = select(AnalysisTaskModel).where(AnalysisTaskModel.user_id == user_id)
            if status:
                stmt = stmt.where(AnalysisTaskModel.status == status.value)
            stmt = stmt.order_by(AnalysisTaskModel.created_at.desc()).offset(offset).limit(limit)
            rows = (await s.execute(stmt)).scalars().all()
            return [mappers.task_to_domain(r) for r in rows]

    async def list_all(self, offset: int = 0, limit: int = 20) -> list[AnalysisTask]:
        async with self._sf() as s:
            stmt = (
                select(AnalysisTaskModel)
                .order_by(AnalysisTaskModel.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            rows = (await s.execute(stmt)).scalars().all()
            return [mappers.task_to_domain(r) for r in rows]

    async def count_all(self) -> int:
        async with self._sf() as s:
            stmt = select(func.count()).select_from(AnalysisTaskModel)
            return int((await s.execute(stmt)).scalar_one())

    async def list_pending_reviews(self) -> list[AnalysisTask]:
        async with self._sf() as s:
            stmt = select(AnalysisTaskModel).where(
                AnalysisTaskModel.status == TaskStatus.waiting_review.value
            )
            rows = (await s.execute(stmt)).scalars().all()
            return [mappers.task_to_domain(r) for r in rows]

    async def save_review(self, review: ReviewRecord) -> ReviewRecord:
        async with self._sf() as s:
            existing = await s.get(ReviewRecordModel, review.id)
            orm = mappers.review_to_orm(review, existing)
            if existing is None:
                s.add(orm)
            await s.commit()
            return review

    async def get_reviews_by_task(self, task_id: UUID) -> list[ReviewRecord]:
        async with self._sf() as s:
            stmt = (
                select(ReviewRecordModel)
                .where(ReviewRecordModel.task_id == task_id)
                .order_by(ReviewRecordModel.created_at.asc())
            )
            rows = (await s.execute(stmt)).scalars().all()
            return [mappers.review_to_domain(r) for r in rows]
