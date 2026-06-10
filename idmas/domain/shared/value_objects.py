"""
共享值对象（Shared Value Objects）。
值对象是不可变的，用 frozen=True 保证。
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, model_validator


class UserRole(str, Enum):
    engineer = "engineer"    # 工程师（设计/工艺/质检/运维）
    reviewer = "reviewer"    # 人工审核员
    admin    = "admin"       # 管理员


# ------------------------------------------------------------------
# Confidence（置信度）
# ------------------------------------------------------------------

class Confidence(BaseModel):
    """
    置信度值对象（0.0 ~ 1.0）。
    - >= HIGH_THRESHOLD (0.85)：高置信，自动通过
    - < LOW_THRESHOLD  (0.60)：低置信，触发人工审核
    """
    model_config = {"frozen": True}

    HIGH_THRESHOLD: float = 0.85
    LOW_THRESHOLD:  float = 0.60

    value: Annotated[float, Field(ge=0.0, le=1.0)]

    @property
    def is_high(self) -> bool:
        return self.value >= self.HIGH_THRESHOLD

    @property
    def is_low(self) -> bool:
        return self.value < self.LOW_THRESHOLD

    @property
    def needs_review(self) -> bool:
        return self.is_low

    def __float__(self) -> float:
        return self.value

    def __repr__(self) -> str:
        level = "HIGH" if self.is_high else ("LOW" if self.is_low else "MID")
        return f"Confidence({self.value:.2f}, {level})"


# ------------------------------------------------------------------
# RequestId
# ------------------------------------------------------------------

class RequestId(BaseModel):
    """请求 ID 值对象，确保每次请求可追溯。"""
    model_config = {"frozen": True}

    value: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @classmethod
    def new(cls) -> "RequestId":
        return cls(value=str(uuid.uuid4()))

    def __str__(self) -> str:
        return self.value


# ------------------------------------------------------------------
# Pagination
# ------------------------------------------------------------------

class Pagination(BaseModel):
    """分页参数值对象。"""
    model_config = {"frozen": True}

    offset: Annotated[int, Field(ge=0)]        = 0
    limit:  Annotated[int, Field(ge=1, le=100)] = 20

    @property
    def page(self) -> int:
        """基于 1 的页码（便于日志输出）。"""
        return self.offset // self.limit + 1


# ------------------------------------------------------------------
# DateRange
# ------------------------------------------------------------------

from datetime import datetime  # noqa: E402  (放在用到的地方，避免循环)


class DateRange(BaseModel):
    """日期范围值对象。start 必须 <= end。"""
    model_config = {"frozen": True}

    start: datetime
    end:   datetime

    @model_validator(mode="after")
    def validate_range(self) -> "DateRange":
        if self.start > self.end:
            raise ValueError(f"start ({self.start}) must be <= end ({self.end})")
        return self

    @property
    def duration_days(self) -> float:
        return (self.end - self.start).total_seconds() / 86400
