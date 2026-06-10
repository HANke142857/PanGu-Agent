"""解析任务 Schema。"""
from __future__ import annotations
from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field
from idmas.domain.analysis.value_objects import PromptMode, TaskStatus, TaskType


# ── 请求 ──────────────────────────────────────────────────────────────────

class LabelReview(BaseModel):
    label_id:       str
    action:         str              # confirm | correct | reject
    corrected_name: str | None = None


class TaskCreateRequest(BaseModel):
    drawing_id:  UUID
    question:    str         = ""
    background:  str         = ""
    task_type:   TaskType    = TaskType.label_recognition
    prompt_mode: PromptMode  = PromptMode.standard_visual


class TaskReviewRequest(BaseModel):
    reviews: list[LabelReview]


# ── 响应 ──────────────────────────────────────────────────────────────────

class TaskCreateResponse(BaseModel):
    task_id:    UUID
    status:     TaskStatus
    stream_url: str


class TaskDetailResponse(BaseModel):
    id:                UUID
    status:            TaskStatus
    drawing_id:        UUID
    task_type:         TaskType
    prompt_mode:       PromptMode
    question:          str
    vision_result:     dict[str, Any] = Field(default_factory=dict)
    conflicts:         list[Any]      = Field(default_factory=list)
    human_decision:    str | None     = None
    inference_time_ms: int | None     = None
    total_tokens:      int            = 0
    error_code:        str | None     = None
    error_message:     str | None     = None
    created_at:        datetime
    updated_at:        datetime


class TaskListResponse(BaseModel):
    items:  list[TaskDetailResponse]
    total:  int
    offset: int
    limit:  int
