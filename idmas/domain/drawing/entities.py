"""
图纸领域实体。

Drawing     ── 聚合根，代表一张工业图纸
DrawingLabel── 图纸上的单个标号（识别结果）
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from idmas.domain.shared.value_objects import Confidence
from idmas.domain.drawing.value_objects import (
    BoundingBox,
    DrawingType,
    FileFormat,
    ImageDimension,
    LifecycleState,
    SpatialInfo,
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> UUID:
    return uuid.uuid4()


# ------------------------------------------------------------------
# DrawingLabel（标号）
# ------------------------------------------------------------------

class LabelSource(str):
    """标号来源标记。"""
    VISION_AGENT = "vision_agent"
    OCR          = "ocr"
    HUMAN        = "human"


class DrawingLabel(BaseModel):
    """
    图纸标号实体。
    一张图纸可含多个标号，每个标号由 Vision Agent 或 OCR 识别，
    或由人工录入/修正。
    """
    id:           UUID       = Field(default_factory=_new_uuid)
    drawing_id:   UUID                          # 所属图纸
    label_id:     str                           # 标号编号，如 "1"、"2A"
    name:         str                           # 标号名称，如 "轴承座"
    confidence:   Confidence
    bounding_box: BoundingBox
    spatial_info: SpatialInfo
    source:       str        = LabelSource.VISION_AGENT
    created_at:   datetime   = Field(default_factory=_now_utc)
    updated_at:   datetime   = Field(default_factory=_now_utc)

    model_config = {"frozen": False}  # 标号可被人工修正

    def correct(self, new_name: str) -> None:
        """人工修正标号名称，同时将 source 标记为 human。"""
        self.name       = new_name
        self.source     = LabelSource.HUMAN
        self.updated_at = _now_utc()

    @property
    def needs_review(self) -> bool:
        return self.confidence.needs_review


# ------------------------------------------------------------------
# Drawing（聚合根）
# ------------------------------------------------------------------

class Drawing(BaseModel):
    """
    图纸聚合根。
    负责维护图纸元数据、生命周期状态，以及与 PLM 系统的关联。
    标号列表（DrawingLabel）通过 DrawingRepository 单独存取，
    聚合根本身只持有 ID 引用（避免过大聚合）。
    """
    id:              UUID          = Field(default_factory=_new_uuid)
    source_system:   str           = ""    # Teamcenter / ENOVIA / IntePLM / manual
    source_doc_id:   str           = ""    # PLM 系统内文档 ID
    title:           str
    drawing_type:    DrawingType
    file_format:     FileFormat
    file_url:        str           = ""    # MinIO 文件 URL
    file_size_bytes: int           = 0
    dimension:       ImageDimension | None = None
    lifecycle_state: LifecycleState = LifecycleState.draft
    metadata:        dict[str, Any] = Field(default_factory=dict)
    created_by:      UUID | None   = None  # 上传用户 ID
    created_at:      datetime      = Field(default_factory=_now_utc)
    updated_at:      datetime      = Field(default_factory=_now_utc)

    model_config = {"frozen": False}

    # ------------------------------------------------------------------
    # 业务方法
    # ------------------------------------------------------------------

    def release(self) -> None:
        """发布图纸（draft → released）。"""
        from idmas.domain.shared.exceptions import InvalidTaskStateError
        if self.lifecycle_state != LifecycleState.draft:
            raise InvalidTaskStateError(self.lifecycle_state.value, LifecycleState.released.value)
        self.lifecycle_state = LifecycleState.released
        self.updated_at = _now_utc()

    def obsolete(self) -> None:
        """废弃图纸（released → obsolete）。"""
        from idmas.domain.shared.exceptions import InvalidTaskStateError
        if self.lifecycle_state != LifecycleState.released:
            raise InvalidTaskStateError(self.lifecycle_state.value, LifecycleState.obsolete.value)
        self.lifecycle_state = LifecycleState.obsolete
        self.updated_at = _now_utc()

    def update_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value
        self.updated_at = _now_utc()

    @property
    def is_image(self) -> bool:
        return self.file_format in (FileFormat.png, FileFormat.jpg)

    @property
    def is_cad(self) -> bool:
        return self.file_format in (FileFormat.dwg, FileFormat.dxf)

    def __repr__(self) -> str:
        return (
            f"Drawing(id={self.id}, title={self.title!r}, "
            f"type={self.drawing_type.value}, state={self.lifecycle_state.value})"
        )
