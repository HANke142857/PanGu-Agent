"""Process SubGraph 状态定义。"""
from __future__ import annotations
from typing import Any
from typing_extensions import TypedDict


class ProcessState(TypedDict, total=False):
    labels:              list[dict[str, Any]]
    drawing_type:        str
    process_params:      dict[str, Any] | None
    param_check_results: list[dict[str, Any]]
    sequence_check:      dict[str, Any] | None
    warnings:            list[str]
    final_result:        dict[str, Any] | None
