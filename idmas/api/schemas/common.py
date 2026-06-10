"""通用响应 Schema。"""
from __future__ import annotations
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code:        str
    message:     str
    detail:      str | None = None   # 仅开发环境暴露
    retry_after: int | None = None
    request_id:  str        = ""


class ErrorResponse(BaseModel):
    error: ErrorDetail


class PaginationParams(BaseModel):
    offset: int = Field(default=0,  ge=0)
    limit:  int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel, Generic[T]):
    items:  list[T]
    total:  int
    offset: int
    limit:  int


class HealthResponse(BaseModel):
    status:       str               # "healthy" | "unhealthy"
    version:      str = "0.1.0"
    dependencies: dict[str, str] = Field(default_factory=dict)
