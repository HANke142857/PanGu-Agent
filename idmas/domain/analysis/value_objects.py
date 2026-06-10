"""
解析任务领域值对象。
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    label_recognition = "label_recognition"   # 标号识别（核心）
    design_analysis   = "design_analysis"     # 设计规范分析
    process_check     = "process_check"       # 工艺参数校验
    knowledge_query   = "knowledge_query"     # 知识检索问答
    comprehensive     = "comprehensive"       # 综合解析（全链路）


class TaskStatus(str, Enum):
    created        = "created"          # 已创建，待处理
    processing     = "processing"       # Agent 处理中
    waiting_review = "waiting_review"   # 等待人工审核
    completed      = "completed"        # 完成
    failed         = "failed"           # 失败


class PromptMode(str, Enum):
    standard_visual  = "standard_visual"    # 标准视觉提示
    cot_visual       = "cot_visual"         # Chain-of-Thought 视觉提示
    few_shot_visual  = "few_shot_visual"    # Few-Shot 视觉提示


class ReviewAction(str, Enum):
    confirm = "confirm"   # 确认 Agent 结果正确
    correct = "correct"   # 修正 Agent 结果
    reject  = "reject"    # 拒绝，标记为无效


class FeedbackStatus(str, Enum):
    pending  = "pending"    # 反馈待纳入知识库
    approved = "approved"   # 已纳入训练集
    rejected = "rejected"   # 数据质量不达标，不纳入


# ------------------------------------------------------------------
# ConflictInfo（冲突信息）
# ------------------------------------------------------------------

class ConflictInfo(BaseModel):
    """
    多 Agent 冲突记录值对象。
    当 Vision Agent 与 Knowledge Agent 对同一标号判断不一致时生成。
    """
    model_config = {"frozen": True}

    label_id:             str
    vision_name:          str
    knowledge_name:       str
    vision_confidence:    float = Field(ge=0.0, le=1.0)
    knowledge_confidence: float = Field(ge=0.0, le=1.0)
    resolution:           str | None = None   # 对抗辩论的裁决结果

    @property
    def is_resolved(self) -> bool:
        return self.resolution is not None


# ------------------------------------------------------------------
# DebateRound（辩论轮次）
# ------------------------------------------------------------------

class DebateRound(BaseModel):
    """对抗辩论单轮记录值对象。"""
    model_config = {"frozen": True}

    round_number:      int
    vision_evidence:   str    # Vision Agent 本轮提供的证据
    knowledge_evidence: str   # Knowledge Agent 本轮提供的证据
    judge_result:      str | None = None   # 裁判（Master）本轮裁决
