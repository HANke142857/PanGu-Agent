"""Process Agent 节点（MVP：规则式工艺检查）。"""
from __future__ import annotations
from typing import Any
from idmas.agents.process.state import ProcessState

# 关键词：带有这些词的标号很可能是工艺相关
_PROCESS_KEYWORDS = {"轴", "齿轮", "轴承", "螺栓", "螺母", "销", "键", "卡环"}


def extract_params_node(state: ProcessState) -> dict[str, Any]:
    labels = state.get("labels") or []
    params: dict[str, Any] = {
        "label_count": len(labels),
        "process_labels": [
            lbl for lbl in labels
            if any(kw in str(lbl.get("name", "")) for kw in _PROCESS_KEYWORDS)
        ],
    }
    return {"process_params": params}


def check_params_node(state: ProcessState) -> dict[str, Any]:
    params  = state.get("process_params") or {}
    results = []
    warnings = []
    for lbl in params.get("process_labels", []):
        conf = float(lbl.get("confidence", 1.0))
        ok   = conf >= 0.75
        results.append({"label_id": lbl.get("label_id"), "name": lbl.get("name"), "ok": ok})
        if not ok:
            warnings.append(f"标号 {lbl.get('label_id')}({lbl.get('name')}) 置信度不足，建议人工确认工艺参数")
    return {"param_check_results": results, "warnings": warnings}


def check_sequence_node(state: ProcessState) -> dict[str, Any]:
    params  = state.get("process_params") or {}
    count   = params.get("label_count", 0)
    seq_ok  = count > 0
    return {"sequence_check": {"label_count": count, "sequence_ok": seq_ok}}


def process_finalize_node(state: ProcessState) -> dict[str, Any]:
    results  = state.get("param_check_results") or []
    warnings = state.get("warnings") or []
    seq      = state.get("sequence_check") or {}
    return {
        "final_result": {
            "process_label_count": len(results),
            "all_ok":   all(r.get("ok") for r in results) if results else True,
            "warnings": warnings,
            "sequence": seq,
        }
    }
