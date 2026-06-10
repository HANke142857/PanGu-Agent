"""
领域层单元测试。
覆盖：值对象校验、实体创建、状态机、领域异常。
无需数据库或网络——纯内存运行。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

# ---------- shared ----------
from idmas.domain.shared.value_objects import Confidence, DateRange, Pagination, RequestId
from idmas.domain.shared.exceptions import (
    DrawingNotFoundError,
    InvalidDrawingError,
    InvalidTaskStateError,
    LowConfidenceError,
    RateLimitExceededError,
)

# ---------- drawing ----------
from idmas.domain.drawing.value_objects import (
    BoundingBox,
    DrawingType,
    FileFormat,
    ImageDimension,
    LifecycleState,
    SpatialInfo,
)
from idmas.domain.drawing.entities import Drawing, DrawingLabel, LabelSource

# ---------- analysis ----------
from idmas.domain.analysis.value_objects import (
    ConflictInfo,
    DebateRound,
    ReviewAction,
    TaskStatus,
    TaskType,
)
from idmas.domain.analysis.entities import AnalysisTask, ReviewRecord

# ---------- knowledge ----------
from idmas.domain.knowledge.entities import DocType, FaultRecord, KnowledgeDocument, Part


# =============================================================================
# Helpers
# =============================================================================

def make_bbox(x=0.1, y=0.1, w=0.2, h=0.2) -> BoundingBox:
    return BoundingBox(x=x, y=y, width=w, height=h)


def make_drawing(**kwargs) -> Drawing:
    defaults = dict(
        title="齿轮箱装配图",
        drawing_type=DrawingType.assembly,
        file_format=FileFormat.png,
    )
    defaults.update(kwargs)
    return Drawing(**defaults)


def make_task(**kwargs) -> AnalysisTask:
    defaults = dict(drawing_id=uuid.uuid4(), user_id=uuid.uuid4())
    defaults.update(kwargs)
    return AnalysisTask(**defaults)


# =============================================================================
# Confidence
# =============================================================================

class TestConfidence:
    def test_high_confidence(self):
        c = Confidence(value=0.90)
        assert c.is_high
        assert not c.is_low
        assert not c.needs_review

    def test_low_confidence(self):
        c = Confidence(value=0.55)
        assert c.is_low
        assert not c.is_high
        assert c.needs_review

    def test_mid_confidence(self):
        c = Confidence(value=0.72)
        assert not c.is_high
        assert not c.is_low

    def test_boundary_high(self):
        assert Confidence(value=0.85).is_high

    def test_boundary_low(self):
        assert not Confidence(value=0.60).is_low   # 0.60 不低于阈值

    def test_out_of_range(self):
        with pytest.raises(ValidationError):
            Confidence(value=1.01)
        with pytest.raises(ValidationError):
            Confidence(value=-0.01)

    def test_float_cast(self):
        assert float(Confidence(value=0.75)) == 0.75


# =============================================================================
# BoundingBox
# =============================================================================

class TestBoundingBox:
    def test_valid_box(self):
        bbox = make_bbox()
        assert bbox.area == pytest.approx(0.04)
        cx, cy = bbox.center
        assert cx == pytest.approx(0.2)
        assert cy == pytest.approx(0.2)

    def test_overflow_x(self):
        with pytest.raises(ValidationError):
            BoundingBox(x=0.9, y=0.1, width=0.2, height=0.2)

    def test_overflow_y(self):
        with pytest.raises(ValidationError):
            BoundingBox(x=0.1, y=0.9, width=0.2, height=0.2)

    def test_zero_width(self):
        with pytest.raises(ValidationError):
            BoundingBox(x=0.1, y=0.1, width=0.0, height=0.2)

    def test_frozen(self):
        bbox = make_bbox()
        with pytest.raises(Exception):
            bbox.x = 0.5  # type: ignore[misc]


# =============================================================================
# SpatialInfo
# =============================================================================

class TestSpatialInfo:
    def test_from_bbox_top_left(self):
        bbox = BoundingBox(x=0.0, y=0.0, width=0.3, height=0.3)
        si = SpatialInfo.from_bounding_box(bbox)
        from idmas.domain.drawing.value_objects import Quadrant
        assert si.quadrant == Quadrant.top_left

    def test_from_bbox_bottom_right(self):
        bbox = BoundingBox(x=0.6, y=0.6, width=0.3, height=0.3)
        si = SpatialInfo.from_bounding_box(bbox)
        from idmas.domain.drawing.value_objects import Quadrant
        assert si.quadrant == Quadrant.bottom_right


# =============================================================================
# ImageDimension
# =============================================================================

class TestImageDimension:
    def test_valid(self):
        dim = ImageDimension(width=1920, height=1080)
        assert dim.aspect_ratio == pytest.approx(16 / 9)
        assert dim.megapixels == pytest.approx(2.0736)

    def test_exceed_max(self):
        with pytest.raises(InvalidDrawingError):
            ImageDimension(width=4097, height=1080)

    def test_exact_max(self):
        dim = ImageDimension(width=4096, height=4096)
        assert dim.width == 4096


# =============================================================================
# Drawing Entity
# =============================================================================

class TestDrawing:
    def test_create(self):
        d = make_drawing()
        assert d.lifecycle_state == LifecycleState.draft
        assert isinstance(d.id, uuid.UUID)

    def test_release(self):
        d = make_drawing()
        d.release()
        assert d.lifecycle_state == LifecycleState.released

    def test_obsolete(self):
        d = make_drawing()
        d.release()
        d.obsolete()
        assert d.lifecycle_state == LifecycleState.obsolete

    def test_invalid_release_from_obsolete(self):
        d = make_drawing()
        d.release()
        d.obsolete()
        with pytest.raises(InvalidTaskStateError):
            d.release()

    def test_invalid_obsolete_from_draft(self):
        d = make_drawing()
        with pytest.raises(InvalidTaskStateError):
            d.obsolete()

    def test_is_image(self):
        d = make_drawing(file_format=FileFormat.png)
        assert d.is_image
        assert not d.is_cad

    def test_is_cad(self):
        d = make_drawing(file_format=FileFormat.dwg)
        assert d.is_cad
        assert not d.is_image

    def test_update_metadata(self):
        d = make_drawing()
        d.update_metadata("source_system", "Teamcenter")
        assert d.metadata["source_system"] == "Teamcenter"


# =============================================================================
# DrawingLabel Entity
# =============================================================================

class TestDrawingLabel:
    def make_label(self) -> DrawingLabel:
        bbox = make_bbox()
        return DrawingLabel(
            drawing_id=uuid.uuid4(),
            label_id="1",
            name="轴承座",
            confidence=Confidence(value=0.92),
            bounding_box=bbox,
            spatial_info=SpatialInfo.from_bounding_box(bbox),
        )

    def test_create(self):
        label = self.make_label()
        assert label.source == LabelSource.VISION_AGENT
        assert not label.needs_review

    def test_correct(self):
        label = self.make_label()
        label.correct("轴承盖")
        assert label.name == "轴承盖"
        assert label.source == LabelSource.HUMAN

    def test_low_confidence_needs_review(self):
        bbox = make_bbox()
        label = DrawingLabel(
            drawing_id=uuid.uuid4(),
            label_id="2",
            name="未知部件",
            confidence=Confidence(value=0.45),
            bounding_box=bbox,
            spatial_info=SpatialInfo.from_bounding_box(bbox),
        )
        assert label.needs_review


# =============================================================================
# AnalysisTask State Machine
# =============================================================================

class TestAnalysisTask:
    def test_create_defaults(self):
        task = make_task()
        assert task.status == TaskStatus.created
        assert task.task_type == TaskType.label_recognition

    def test_mark_processing(self):
        task = make_task()
        task.mark_processing(thread_id="thread-abc-123")
        assert task.status == TaskStatus.processing
        assert task.langgraph_thread_id == "thread-abc-123"

    def test_mark_completed(self):
        task = make_task()
        task.mark_processing("t1")
        task.mark_completed(inference_time_ms=12000, total_tokens=4096)
        assert task.status == TaskStatus.completed
        assert task.inference_time_ms == 12000

    def test_mark_failed(self):
        task = make_task()
        task.mark_processing("t1")
        task.mark_failed("IDMAS-502-002", "GPU OOM")
        assert task.status == TaskStatus.failed
        assert task.error_code == "IDMAS-502-002"

    def test_invalid_transition(self):
        task = make_task()
        with pytest.raises(InvalidTaskStateError):
            task.transition_to(TaskStatus.completed)  # created → completed 非法

    def test_conflict_tracking(self):
        task = make_task()
        conflict = ConflictInfo(
            label_id="1",
            vision_name="轴承座",
            knowledge_name="轴承盖",
            vision_confidence=0.82,
            knowledge_confidence=0.90,
        )
        task.add_conflict(conflict)
        assert task.has_conflicts
        assert not task.all_conflicts_resolved

    def test_waiting_review_and_complete(self):
        task = make_task()
        task.mark_processing("t1")
        task.mark_waiting_review()
        assert task.status == TaskStatus.waiting_review
        task.mark_completed(5000, 1024)
        assert task.status == TaskStatus.completed


# =============================================================================
# ConflictInfo & DebateRound
# =============================================================================

class TestConflictAndDebate:
    def test_conflict_unresolved(self):
        c = ConflictInfo(
            label_id="3",
            vision_name="A",
            knowledge_name="B",
            vision_confidence=0.7,
            knowledge_confidence=0.8,
        )
        assert not c.is_resolved

    def test_conflict_resolved(self):
        c = ConflictInfo(
            label_id="3",
            vision_name="A",
            knowledge_name="B",
            vision_confidence=0.7,
            knowledge_confidence=0.8,
            resolution="knowledge_wins",
        )
        assert c.is_resolved

    def test_debate_round(self):
        r = DebateRound(
            round_number=1,
            vision_evidence="图像显示圆形轮廓",
            knowledge_evidence="手册记载该位置为轴承盖",
        )
        assert r.judge_result is None


# =============================================================================
# KnowledgeDocument & FaultRecord
# =============================================================================

class TestKnowledgeEntities:
    def test_document_create(self):
        doc = KnowledgeDocument(
            title="电机维修手册 v3",
            content="第5章：轴承更换步骤...",
            doc_type=DocType.manual,
            source="设备手册 YE3-160M",
        )
        assert doc.doc_type == DocType.manual
        doc.add_tag("轴承")
        assert "轴承" in doc.tags

    def test_fault_record_verify(self):
        fr = FaultRecord(
            code="F001",
            description="电机过热",
            symptoms=["温度异常", "电流偏高"],
            root_cause="轴承磨损",
            solution="更换轴承，重新对中",
        )
        assert not fr.verified
        fr.verify()
        assert fr.verified


# =============================================================================
# Shared Value Objects
# =============================================================================

class TestSharedValueObjects:
    def test_pagination_page(self):
        p = Pagination(offset=40, limit=20)
        assert p.page == 3

    def test_request_id_unique(self):
        ids = {str(RequestId.new()) for _ in range(100)}
        assert len(ids) == 100

    def test_date_range_valid(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end   = datetime(2026, 1, 31, tzinfo=timezone.utc)
        dr = DateRange(start=start, end=end)
        assert dr.duration_days == pytest.approx(30.0)

    def test_date_range_invalid(self):
        start = datetime(2026, 2, 1, tzinfo=timezone.utc)
        end   = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(ValidationError):
            DateRange(start=start, end=end)


# =============================================================================
# Domain Exceptions
# =============================================================================

class TestDomainExceptions:
    def test_drawing_not_found(self):
        err = DrawingNotFoundError("abc-123")
        assert "abc-123" in err.message
        assert err.http_status == 404
        assert err.code == "IDMAS-404-001"

    def test_low_confidence_error(self):
        err = LowConfidenceError(confidence=0.45, threshold=0.60)
        assert "0.45" in err.message
        assert err.http_status == 422

    def test_rate_limit_error(self):
        err = RateLimitExceededError(retry_after=120)
        assert err.retry_after == 120
        assert err.http_status == 429

    def test_invalid_task_state(self):
        err = InvalidTaskStateError("created", "completed")
        assert "created" in err.message
        assert "completed" in err.message
