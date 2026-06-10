"""图纸管理 Schema。"""
from __future__ import annotations
from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field
from idmas.domain.drawing.value_objects import DrawingType, FileFormat, LifecycleState


# ── 请求 ──────────────────────────────────────────────────────────────────

class DrawingCreateRequest(BaseModel):
    """POST /api/v1/drawings 请求体（file 通过 multipart 独立传）。"""
    title:          str
    drawing_type:   DrawingType  = DrawingType.assembly
    source_system:  str | None   = None
    source_doc_id:  str | None   = None
    metadata:       dict[str, Any] = Field(default_factory=dict)
    prompt_mode:    str          = "standard_visual"   # 同时触发解析用


# ── 标号 ──────────────────────────────────────────────────────────────────

class LabelResponse(BaseModel):
    label_id:            str
    name:                str
    confidence:          float
    needs_review:        bool
    spatial_description: str | None = None
    quadrant:            str | None = None
    bounding_box:        dict[str, float] | None = None


# ── 响应 ──────────────────────────────────────────────────────────────────

class DrawingResponse(BaseModel):
    id:              UUID
    title:           str
    drawing_type:    DrawingType
    file_format:     FileFormat
    file_url:        str
    file_size_bytes: int
    lifecycle_state: LifecycleState
    source_system:   str
    labels:          list[LabelResponse] = Field(default_factory=list)
    label_count:     int                 = 0
    created_at:      datetime
    updated_at:      datetime


class DrawingListResponse(BaseModel):
    items:  list[DrawingResponse]
    total:  int
    offset: int
    limit:  int
