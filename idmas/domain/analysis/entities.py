"""
解析任务领域实体。

AnalysisTask  ── 聚合根，代表一次完整的图纸解析任务
ReviewRecord  ── 人工审核记录实体
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from idmas.domain.analysis.value_objects import (
    ConflictInfo,
    DebateRound,
    FeedbackStatus,
    PromptMode,
    ReviewAction,
    TaskStatus,
    TaskType,
)
from idmas.domain.shared.exceptions import InvalidTaskStateError


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# 合法的状态流转路径
_VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.created:        {TaskStatus.processing, TaskStatus.failed},
    TaskStatus.processing:     {TaskStatus.waiting_review, TaskStatus.completed, TaskStatus.failed},
    TaskStatus.waiting_review: {TaskStatus.processing, TaskStatus.completed, TaskStatus.failed},
    TaskStatus.completed:      set(),   # 终态
    TaskStatus.failed:         {TaskStatus.created},  # 允许重试
}


class AnalysisTask(BaseModel):
    """
    图纸解析任务聚合根。
    一个任务对应一次多 Agent 协同解析流程，全程状态由此实体管理。
    """
    id:                  UUID        = Field(default_factory=uuid.uuid4)
    drawing_id:          UUID
    user_id:             UUID
    task_type:           TaskType    = TaskType.label_recognition
    prompt_mode:         PromptMode  = PromptMode.standard_visual
    question:            str         = ""    # 用户附加问题（可选）
    background:          str         = ""    # 背景信息（可选）

    status:              TaskStatus  = TaskStatus.created
    langgraph_thread_id: str | None  = None  # LangGraph checkpointer 线程 ID

    # 各 Agent 的输出（原始 dict，下游 schema 解析）
    vision_result:       dict[str, Any] = Field(default_factory=dict)
    ocr_result:          dict[str, Any] = Field(default_factory=dict)
    design_result:       dict[str, Any] = Field(default_factory=dict)
    process_result:      dict[str, Any] = Field(default_factory=dict)
    knowledge_result:    dict[str, Any] = Field(default_factory=dict)
    report_result:       dict[str, Any] = Field(default_factory=dict)

    # 冲突与辩论
    conflicts:           list[ConflictInfo] = Field(default_factory=list)
    debate_rounds:       list[DebateRound]  = Field(default_factory=list)
    human_decision:      str | None         = None  # 人工最终决策

    # 性能指标
    inference_time_ms:   int | None  = None
    total_tokens:        int         = 0
    model_version:       str         = ""

    # 错误信息
    error_code:          str | None  = None
    error_message:       str | None  = None

    created_at:          datetime    = Field(default_factory=_now_utc)
    updated_at:          datetime    = Field(default_factory=_now_utc)

    model_config = {"frozen": False, "protected_namespaces": ()}

    # ------------------------------------------------------------------
    # 状态机
    # ------------------------------------------------------------------

    def transition_to(self, new_status: TaskStatus) -> None:
        """状态流转，非法转换抛 InvalidTaskStateError。"""
        allowed = _VALID_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise InvalidTaskStateError(self.status.value, new_status.value)
        self.status     = new_status
        self.updated_at = _now_utc()

    def mark_processing(self, thread_id: str) -> None:
        self.langgraph_thread_id = thread_id
        self.transition_to(TaskStatus.processing)

    def mark_waiting_review(self) -> None:
        self.transition_to(TaskStatus.waiting_review)

    def mark_completed(self, inference_time_ms: int, total_tokens: int) -> None:
        self.inference_time_ms = inference_time_ms
        self.total_tokens      = total_tokens
        self.transition_to(TaskStatus.completed)

    def mark_failed(self, error_code: str, error_message: str) -> None:
        self.error_code    = error_code
        self.error_message = error_message
        self.transition_to(TaskStatus.failed)

    # ------------------------------------------------------------------
    # 业务方法
    # ------------------------------------------------------------------

    def add_conflict(self, conflict: ConflictInfo) -> None:
        self.conflicts.append(conflict)
        self.updated_at = _now_utc()

    def add_debate_round(self, round_: DebateRound) -> None:
        self.debate_rounds.append(round_)
        self.updated_at = _now_utc()

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicts)

    @property
    def all_conflicts_resolved(self) -> bool:
        return all(c.is_resolved for c in self.conflicts)

    def __repr__(self) -> str:
        return (
            f"AnalysisTask(id={self.id}, type={self.task_type.value}, "
            f"status={self.status.value})"
        )


# ------------------------------------------------------------------
# ReviewRecord（审核记录）
# ------------------------------------------------------------------

class ReviewRecord(BaseModel):
    """人工审核记录实体。每次人工修正/确认对应一条记录，用于反馈闭环。"""

    id:              UUID          = Field(default_factory=uuid.uuid4)
    task_id:         UUID
    reviewer_id:     UUID
    label_id:        str
    original_name:   str
    corrected_name:  str | None    = None   # 仅 action=correct 时有值
    action:          ReviewAction
    feedback_status: FeedbackStatus = FeedbackStatus.pending
    note:            str           = ""
    created_at:      datetime      = Field(default_factory=_now_utc)

    model_config = {"frozen": False}

    def approve_feedback(self) -> None:
        """数据质检通过，纳入训练集。"""
        self.feedback_status = FeedbackStatus.approved

    def reject_feedback(self) -> None:
        """数据质检不通过，不纳入训练集。"""
        self.feedback_status = FeedbackStatus.rejected
