"""
ORM 模型 ↔ domain 实体 的双向映射。

放在单独模块，使仓储实现保持精简，也便于单测映射逻辑本身。
原则：domain 实体是唯一真实来源，ORM 仅作持久化载体。
"""

from __future__ import annotations

from idmas.domain.analysis.entities import AnalysisTask, ReviewRecord
from idmas.domain.analysis.value_objects import ConflictInfo, DebateRound
from idmas.domain.drawing.entities import Drawing, DrawingLabel
from idmas.domain.drawing.value_objects import BoundingBox, ImageDimension, SpatialInfo
from idmas.domain.shared.value_objects import Confidence
from idmas.infrastructure.db.models import (
    AnalysisTaskModel,
    DrawingLabelModel,
    DrawingModel,
    ReviewRecordModel,
)


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def drawing_to_orm(d: Drawing, orm: DrawingModel | None = None) -> DrawingModel:
    orm = orm or DrawingModel()
    orm.id              = d.id
    orm.source_system   = d.source_system
    orm.source_doc_id   = d.source_doc_id
    orm.title           = d.title
    orm.drawing_type    = d.drawing_type.value
    orm.file_format     = d.file_format.value
    orm.file_url        = d.file_url
    orm.file_size_bytes = d.file_size_bytes
    orm.image_width     = d.dimension.width  if d.dimension else None
    orm.image_height    = d.dimension.height if d.dimension else None
    orm.lifecycle_state = d.lifecycle_state.value
    orm.doc_metadata    = dict(d.metadata)
    orm.created_by      = d.created_by
    orm.created_at      = d.created_at
    orm.updated_at      = d.updated_at
    return orm


def drawing_to_domain(orm: DrawingModel) -> Drawing:
    dimension = None
    if orm.image_width is not None and orm.image_height is not None:
        dimension = ImageDimension(width=orm.image_width, height=orm.image_height)
    return Drawing(
        id=orm.id,
        source_system=orm.source_system,
        source_doc_id=orm.source_doc_id,
        title=orm.title,
        drawing_type=orm.drawing_type,
        file_format=orm.file_format,
        file_url=orm.file_url,
        file_size_bytes=orm.file_size_bytes,
        dimension=dimension,
        lifecycle_state=orm.lifecycle_state,
        metadata=dict(orm.doc_metadata or {}),
        created_by=orm.created_by,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


# ---------------------------------------------------------------------------
# DrawingLabel
# ---------------------------------------------------------------------------

def label_to_orm(label: DrawingLabel, orm: DrawingLabelModel | None = None) -> DrawingLabelModel:
    orm = orm or DrawingLabelModel()
    orm.id           = label.id
    orm.drawing_id   = label.drawing_id
    orm.label_id     = label.label_id
    orm.name         = label.name
    orm.confidence   = label.confidence.value
    orm.bounding_box = label.bounding_box.model_dump()
    orm.spatial_info = label.spatial_info.model_dump()
    orm.source       = label.source
    orm.created_at   = label.created_at
    orm.updated_at   = label.updated_at
    return orm


def label_to_domain(orm: DrawingLabelModel) -> DrawingLabel:
    return DrawingLabel(
        id=orm.id,
        drawing_id=orm.drawing_id,
        label_id=orm.label_id,
        name=orm.name,
        confidence=Confidence(value=orm.confidence),
        bounding_box=BoundingBox(**orm.bounding_box),
        spatial_info=SpatialInfo(**orm.spatial_info),
        source=orm.source,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


# ---------------------------------------------------------------------------
# AnalysisTask
# ---------------------------------------------------------------------------

def task_to_orm(t: AnalysisTask, orm: AnalysisTaskModel | None = None) -> AnalysisTaskModel:
    orm = orm or AnalysisTaskModel()
    orm.id                  = t.id
    orm.drawing_id          = t.drawing_id
    orm.user_id             = t.user_id
    orm.task_type           = t.task_type.value
    orm.prompt_mode         = t.prompt_mode.value
    orm.question            = t.question
    orm.background          = t.background
    orm.status              = t.status.value
    orm.langgraph_thread_id = t.langgraph_thread_id
    orm.vision_result       = dict(t.vision_result)
    orm.ocr_result          = dict(t.ocr_result)
    orm.design_result       = dict(t.design_result)
    orm.process_result      = dict(t.process_result)
    orm.knowledge_result    = dict(t.knowledge_result)
    orm.report_result       = dict(t.report_result)
    orm.conflicts           = [c.model_dump() for c in t.conflicts]
    orm.debate_rounds       = [r.model_dump() for r in t.debate_rounds]
    orm.human_decision      = t.human_decision
    orm.inference_time_ms   = t.inference_time_ms
    orm.total_tokens        = t.total_tokens
    orm.model_version       = t.model_version
    orm.error_code          = t.error_code
    orm.error_message       = t.error_message
    orm.created_at          = t.created_at
    orm.updated_at          = t.updated_at
    return orm


def task_to_domain(orm: AnalysisTaskModel) -> AnalysisTask:
    return AnalysisTask(
        id=orm.id,
        drawing_id=orm.drawing_id,
        user_id=orm.user_id,
        task_type=orm.task_type,
        prompt_mode=orm.prompt_mode,
        question=orm.question,
        background=orm.background,
        status=orm.status,
        langgraph_thread_id=orm.langgraph_thread_id,
        vision_result=dict(orm.vision_result or {}),
        ocr_result=dict(orm.ocr_result or {}),
        design_result=dict(orm.design_result or {}),
        process_result=dict(orm.process_result or {}),
        knowledge_result=dict(orm.knowledge_result or {}),
        report_result=dict(orm.report_result or {}),
        conflicts=[ConflictInfo(**c) for c in (orm.conflicts or [])],
        debate_rounds=[DebateRound(**r) for r in (orm.debate_rounds or [])],
        human_decision=orm.human_decision,
        inference_time_ms=orm.inference_time_ms,
        total_tokens=orm.total_tokens,
        model_version=orm.model_version,
        error_code=orm.error_code,
        error_message=orm.error_message,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


# ---------------------------------------------------------------------------
# ReviewRecord
# ---------------------------------------------------------------------------

def review_to_orm(r: ReviewRecord, orm: ReviewRecordModel | None = None) -> ReviewRecordModel:
    orm = orm or ReviewRecordModel()
    orm.id              = r.id
    orm.task_id         = r.task_id
    orm.reviewer_id     = r.reviewer_id
    orm.label_id        = r.label_id
    orm.original_name   = r.original_name
    orm.corrected_name  = r.corrected_name
    orm.action          = r.action.value
    orm.feedback_status = r.feedback_status.value
    orm.note            = r.note
    orm.created_at      = r.created_at
    return orm


def review_to_domain(orm: ReviewRecordModel) -> ReviewRecord:
    return ReviewRecord(
        id=orm.id,
        task_id=orm.task_id,
        reviewer_id=orm.reviewer_id,
        label_id=orm.label_id,
        original_name=orm.original_name,
        corrected_name=orm.corrected_name,
        action=orm.action,
        feedback_status=orm.feedback_status,
        note=orm.note,
        created_at=orm.created_at,
    )
