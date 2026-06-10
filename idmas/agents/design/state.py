"""Design SubGraph 状态定义。"""
from __future__ import annotations
from typing import Any
from typing_extensions import TypedDict


class DesignState(TypedDict, total=False):
    labels:             list[dict[str, Any]]   # 来自 Vision 的标号列表
    drawing_type:       str
    design_standards:   list[dict[str, Any]]   # 匹配到的设计标准
    compliance_results: list[dict[str, Any]]   # 合规检查结果
    bom_check:          dict[str, Any] | None  # BOM 一致性
    suggestions:        list[str]              # 改进建议
    final_result:       dict[str, Any] | None
