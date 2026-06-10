"""
Master Graph 全局状态定义 (IDMASState)。
这是贯穿整个多 Agent 协同流程的"血液"。
"""
from __future__ import annotations
import operator
from typing import Annotated, Any
from typing_extensions import TypedDict


class IDMASState(TypedDict, total=False):
    # ── 输入 ─────────────────────────────────────────────────────────
    request_id:     str
    user_id:        str
    user_query:     str
    image_url:      str
    background_text: str | None
    prompt_mode:    str
    task_type:      str   # label_recognition/design_analysis/process_check/knowledge_query/comprehensive

    # ── 意图识别结果 ──────────────────────────────────────────────────
    intent:          str              # 最终确定的意图
    required_agents: list[str]        # 需要调用的 Agent 列表

    # ── 各 Agent 输出 ─────────────────────────────────────────────────
    vision_result:    dict[str, Any] | None
    design_result:    dict[str, Any] | None
    process_result:   dict[str, Any] | None
    knowledge_result: dict[str, Any] | None
    report_result:    dict[str, Any] | None

    # ── 冲突与辩论 ────────────────────────────────────────────────────
    conflicts:          list[dict[str, Any]]   # 检测到的冲突
    debate_rounds:      list[dict[str, Any]]   # 对抗辩论轮次
    debate_resolved:    bool                   # 辩论是否已裁决

    # ── 人工审核 ──────────────────────────────────────────────────────
    human_review_needed: bool
    human_decision:      dict[str, Any] | None  # 人工输入后填入

    # ── 流程控制 ──────────────────────────────────────────────────────
    status:        str          # processing/waiting_review/completed/failed
    error:         str | None
    total_tokens:  int

    # 消息日志（追加语义）
    messages: Annotated[list[dict[str, Any]], operator.add]
