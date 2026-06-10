"""PLM 回写相关 Schema。"""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class PLMWritebackRequest(BaseModel):
    task_id:       UUID
    target_system: str = Field(description="目标 PLM：teamcenter | enovia | inteplm")


class PLMWritebackResponse(BaseModel):
    success:       bool
    doc_id:        str
    target_system: str
    skipped:       bool = False
    message:       str  = ""
