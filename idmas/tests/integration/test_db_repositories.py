"""
DB 持久化层集成测试。

用共享内存 SQLite（StaticPool 保证多 session 复用同一连接）验证：
  - SQLDrawingRepository / SQLAnalysisTaskRepository 实现 domain 契约
  - ORM ↔ domain 映射往返无损（值对象、枚举、JSON 字段）

与 InMemory* 实现行为对齐——同一组断言对两者都应成立。
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from idmas.domain.analysis.entities import AnalysisTask, ReviewRecord
from idmas.domain.analysis.value_objects import (
    ConflictInfo,
    PromptMode,
    ReviewAction,
    TaskStatus,
    TaskType,
)
from idmas.domain.drawing.entities import Drawing, DrawingLabel, LabelSource
from idmas.domain.drawing.value_objects import (
    BoundingBox,
    DrawingType,
    FileFormat,
    ImageDimension,
    LifecycleState,
    SpatialInfo,
)
from idmas.domain.shared.value_objects import Confidence
from idmas.infrastructure.db.models import Base
from idmas.infrastructure.db.repositories import (
    SQLAnalysisTaskRepository,
    SQLDrawingRepository,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def drawing_repo(session_factory):
    return SQLDrawingRepository(session_factory)


@pytest_asyncio.fixture
async def task_repo(session_factory):
    return SQLAnalysisTaskRepository(session_factory)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def make_drawing(**kw) -> Drawing:
    defaults = dict(
        title="齿轮箱装配图",
        drawing_type=DrawingType.assembly,
        file_format=FileFormat.png,
        dimension=ImageDimension(width=1920, height=1080),
        created_by=uuid.uuid4(),
        metadata={"project": "X100"},
    )
    defaults.update(kw)
    return Drawing(**defaults)


def make_label(drawing_id, label_id="1", name="轴承座", conf=0.92) -> DrawingLabel:
    bbox = BoundingBox(x=0.1, y=0.1, width=0.2, height=0.2)
    return DrawingLabel(
        drawing_id=drawing_id,
        label_id=label_id,
        name=name,
        confidence=Confidence(value=conf),
        bounding_box=bbox,
        spatial_info=SpatialInfo.from_bounding_box(bbox, region="左上"),
    )


def make_task(**kw) -> AnalysisTask:
    defaults = dict(
        drawing_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        task_type=TaskType.label_recognition,
        prompt_mode=PromptMode.standard_visual,
    )
    defaults.update(kw)
    return AnalysisTask(**defaults)


# ---------------------------------------------------------------------------
# Drawing repository
# ---------------------------------------------------------------------------

class TestSQLDrawingRepository:
    async def test_save_and_get_roundtrip(self, drawing_repo):
        d = make_drawing()
        await drawing_repo.save(d)
        got = await drawing_repo.get_by_id(d.id)
        assert got is not None
        assert got.id == d.id
        assert got.title == d.title
        assert got.drawing_type is DrawingType.assembly
        assert got.file_format is FileFormat.png
        assert got.dimension == d.dimension          # 值对象往返无损
        assert got.metadata == {"project": "X100"}
        assert got.created_by == d.created_by

    async def test_get_missing_returns_none(self, drawing_repo):
        assert await drawing_repo.get_by_id(uuid.uuid4()) is None

    async def test_save_is_upsert(self, drawing_repo):
        d = make_drawing()
        await drawing_repo.save(d)
        d.title = "改名后的图纸"
        await drawing_repo.save(d)
        got = await drawing_repo.get_by_id(d.id)
        assert got.title == "改名后的图纸"
        # 仍只有一条
        listed = await drawing_repo.list_by_user(d.created_by)
        assert len(listed) == 1

    async def test_list_by_user_isolation(self, drawing_repo):
        u1, u2 = uuid.uuid4(), uuid.uuid4()
        await drawing_repo.save(make_drawing(created_by=u1))
        await drawing_repo.save(make_drawing(created_by=u1))
        await drawing_repo.save(make_drawing(created_by=u2))
        assert len(await drawing_repo.list_by_user(u1)) == 2
        assert len(await drawing_repo.list_by_user(u2)) == 1

    async def test_list_pagination(self, drawing_repo):
        u = uuid.uuid4()
        for i in range(5):
            await drawing_repo.save(make_drawing(created_by=u, title=f"图纸{i}"))
        page = await drawing_repo.list_by_user(u, offset=0, limit=2)
        assert len(page) == 2

    async def test_search_by_title(self, drawing_repo):
        await drawing_repo.save(make_drawing(title="减速器装配图"))
        await drawing_repo.save(make_drawing(title="泵体零件图"))
        hits = await drawing_repo.search_by_title("装配")
        assert len(hits) == 1
        assert hits[0].title == "减速器装配图"

    async def test_delete_is_logical(self, drawing_repo):
        d = make_drawing()
        await drawing_repo.save(d)
        await drawing_repo.delete(d.id)
        got = await drawing_repo.get_by_id(d.id)
        assert got is not None                       # 未物理删除
        assert got.lifecycle_state is LifecycleState.obsolete

    async def test_labels_save_get_and_update(self, drawing_repo):
        d = make_drawing()
        await drawing_repo.save(d)
        labels = [make_label(d.id, "1", "轴承座"), make_label(d.id, "2", "端盖")]
        await drawing_repo.save_labels(labels)

        got = await drawing_repo.get_labels(d.id)
        assert len(got) == 2
        names = {label.name for label in got}
        assert names == {"轴承座", "端盖"}
        # 值对象往返
        sample = got[0]
        assert isinstance(sample.confidence, Confidence)
        assert isinstance(sample.bounding_box, BoundingBox)
        assert isinstance(sample.spatial_info, SpatialInfo)

        # 人工修正 → upsert，不新增
        target = got[0]
        target.correct("修正名称")
        await drawing_repo.update_label(target)
        after = await drawing_repo.get_labels(d.id)
        assert len(after) == 2
        corrected = next(label for label in after if label.id == target.id)
        assert corrected.name == "修正名称"
        assert corrected.source == LabelSource.HUMAN


# ---------------------------------------------------------------------------
# AnalysisTask repository
# ---------------------------------------------------------------------------

class TestSQLAnalysisTaskRepository:
    async def test_save_and_get_roundtrip(self, task_repo):
        t = make_task(question="这是什么标号？")
        await task_repo.save(t)
        got = await task_repo.get_by_id(t.id)
        assert got is not None
        assert got.id == t.id
        assert got.task_type is TaskType.label_recognition
        assert got.status is TaskStatus.created
        assert got.question == "这是什么标号？"

    async def test_update_status(self, task_repo):
        t = make_task()
        await task_repo.save(t)
        await task_repo.update_status(t.id, TaskStatus.processing)
        got = await task_repo.get_by_id(t.id)
        assert got.status is TaskStatus.processing

    async def test_update_result_field(self, task_repo):
        t = make_task()
        await task_repo.save(t)
        await task_repo.update_result(t.id, "vision_result", {"labels": [{"id": "1"}]})
        got = await task_repo.get_by_id(t.id)
        assert got.vision_result == {"labels": [{"id": "1"}]}

    async def test_conflicts_json_roundtrip(self, task_repo):
        t = make_task()
        t.add_conflict(ConflictInfo(
            label_id="1",
            vision_name="轴承座",
            knowledge_name="端盖",
            vision_confidence=0.7,
            knowledge_confidence=0.8,
        ))
        await task_repo.save(t)
        got = await task_repo.get_by_id(t.id)
        assert len(got.conflicts) == 1
        assert got.conflicts[0].vision_name == "轴承座"
        assert got.has_conflicts

    async def test_list_by_user_with_status_filter(self, task_repo):
        u = uuid.uuid4()
        t1 = make_task(user_id=u)
        t2 = make_task(user_id=u)
        t2.mark_processing("thread-1")
        await task_repo.save(t1)
        await task_repo.save(t2)
        assert len(await task_repo.list_by_user(u)) == 2
        processing = await task_repo.list_by_user(u, status=TaskStatus.processing)
        assert len(processing) == 1
        assert processing[0].id == t2.id

    async def test_list_pending_reviews(self, task_repo):
        t = make_task()
        t.mark_processing("th")
        t.mark_waiting_review()
        await task_repo.save(t)
        await task_repo.save(make_task())  # created，不应入队
        pending = await task_repo.list_pending_reviews()
        assert len(pending) == 1
        assert pending[0].id == t.id

    async def test_reviews_save_and_list(self, task_repo):
        t = make_task()
        await task_repo.save(t)
        r = ReviewRecord(
            task_id=t.id,
            reviewer_id=uuid.uuid4(),
            label_id="1",
            original_name="轴承座",
            corrected_name="端盖",
            action=ReviewAction.correct,
        )
        await task_repo.save_review(r)
        got = await task_repo.get_reviews_by_task(t.id)
        assert len(got) == 1
        assert got[0].action is ReviewAction.correct
        assert got[0].corrected_name == "端盖"
