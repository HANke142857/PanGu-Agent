"""Report SubGraph 状态定义。"""
from __future__ import annotations
from typing import Any
from typing_extensions import TypedDict


class ReportState(TypedDict, total=False):
    vision_result:      dict[str, Any] | None
    design_result:      dict[str, Any] | None
    process_result:     dict[str, Any] | None
    knowledge_result:   dict[str, Any] | None
    conflicts_resolved: list[dict[str, Any]]
    human_decisions:    dict[str, Any] | None
    report_sections:    list[dict[str, Any]]
    summary:            str | None
    final_report:       dict[str, Any] | None
