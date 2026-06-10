"""
SQLAlchemy ORM 模型定义。

对应 PostgreSQL DDL（参见技术设计 3.2 节）。为保持测试可在 SQLite 上运行，
跨数据库差异由 GUID TypeDecorator 抹平：
  - PostgreSQL → 原生 UUID
  - 其它（SQLite）→ CHAR(36)

模型与 domain 实体的转换在 mappers.py，仓储只依赖 domain 接口。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    CHAR,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    TypeDecorator,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


# ---------------------------------------------------------------------------
# 跨数据库类型
# ---------------------------------------------------------------------------

class GUID(TypeDecorator):
    """平台无关的 UUID 类型。PostgreSQL 用原生 UUID，其余存为 CHAR(36)。"""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):  # noqa: ANN001
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):  # noqa: ANN001
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(value)

    def process_result_value(self, value, dialect):  # noqa: ANN001
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


# PostgreSQL 用 JSONB（带索引能力），其余回落到通用 JSON。
JSONType = JSON().with_variant(JSONB, "postgresql")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """所有 ORM 模型的声明式基类。"""


# ---------------------------------------------------------------------------
# drawings
# ---------------------------------------------------------------------------

class DrawingModel(Base):
    __tablename__ = "drawings"

    id:              Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    source_system:   Mapped[str]       = mapped_column(String(32),  default="")
    source_doc_id:   Mapped[str]       = mapped_column(String(128), default="")
    title:           Mapped[str]       = mapped_column(String(512), index=True)
    drawing_type:    Mapped[str]       = mapped_column(String(32),  index=True)
    file_format:     Mapped[str]       = mapped_column(String(16))
    file_url:        Mapped[str]       = mapped_column(String(1024), default="")
    file_size_bytes: Mapped[int]       = mapped_column(Integer, default=0)
    image_width:     Mapped[int | None]  = mapped_column(Integer, nullable=True)
    image_height:    Mapped[int | None]  = mapped_column(Integer, nullable=True)
    lifecycle_state: Mapped[str]       = mapped_column(String(16), default="draft")
    # 'metadata' 是 Declarative 的保留属性名，故属性名加前缀，列名仍为 metadata。
    doc_metadata:    Mapped[dict[str, Any]] = mapped_column("metadata", JSONType, default=dict)
    created_by:      Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True, index=True)
    created_at:      Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=_now_utc)
    updated_at:      Mapped[datetime]  = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc
    )


# ---------------------------------------------------------------------------
# drawing_labels
# ---------------------------------------------------------------------------

class DrawingLabelModel(Base):
    __tablename__ = "drawing_labels"

    id:           Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    drawing_id:   Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    label_id:     Mapped[str]       = mapped_column(String(32))
    name:         Mapped[str]       = mapped_column(String(256))
    confidence:   Mapped[float]     = mapped_column(Float)
    bounding_box: Mapped[dict[str, Any]] = mapped_column(JSONType)
    spatial_info: Mapped[dict[str, Any]] = mapped_column(JSONType)
    source:       Mapped[str]       = mapped_column(String(32), default="vision_agent")
    created_at:   Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=_now_utc)
    updated_at:   Mapped[datetime]  = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc
    )


# ---------------------------------------------------------------------------
# analysis_tasks
# ---------------------------------------------------------------------------

class AnalysisTaskModel(Base):
    __tablename__ = "analysis_tasks"

    id:                  Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    drawing_id:          Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    user_id:             Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    task_type:           Mapped[str]       = mapped_column(String(32))
    prompt_mode:         Mapped[str]       = mapped_column(String(32))
    question:            Mapped[str]       = mapped_column(Text, default="")
    background:          Mapped[str]       = mapped_column(Text, default="")

    status:              Mapped[str]       = mapped_column(String(16), index=True, default="created")
    langgraph_thread_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    vision_result:       Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    ocr_result:          Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    design_result:       Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    process_result:      Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    knowledge_result:    Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    report_result:       Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)

    conflicts:           Mapped[list[Any]] = mapped_column(JSONType, default=list)
    debate_rounds:       Mapped[list[Any]] = mapped_column(JSONType, default=list)
    human_decision:      Mapped[str | None] = mapped_column(Text, nullable=True)

    inference_time_ms:   Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens:        Mapped[int]       = mapped_column(Integer, default=0)
    model_version:       Mapped[str]       = mapped_column(String(64), default="")

    error_code:          Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message:       Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at:          Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=_now_utc)
    updated_at:          Mapped[datetime]  = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc
    )


# ---------------------------------------------------------------------------
# review_records
# ---------------------------------------------------------------------------

class ReviewRecordModel(Base):
    __tablename__ = "review_records"

    id:              Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    task_id:         Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    reviewer_id:     Mapped[uuid.UUID] = mapped_column(GUID())
    label_id:        Mapped[str]       = mapped_column(String(32))
    original_name:   Mapped[str]       = mapped_column(String(256))
    corrected_name:  Mapped[str | None] = mapped_column(String(256), nullable=True)
    action:          Mapped[str]       = mapped_column(String(16))
    feedback_status: Mapped[str]       = mapped_column(String(16), default="pending")
    note:            Mapped[str]       = mapped_column(Text, default="")
    created_at:      Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=_now_utc)
