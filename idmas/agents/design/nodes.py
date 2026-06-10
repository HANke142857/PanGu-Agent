"""
Design Agent 节点（MVP：规则式合规检查，无需 LLM）。
检查标号命名是否符合简单的工业命名规范，输出改进建议。
"""
from __future__ import annotations
import logging
from typing import Any
from idmas.agents.design.state import DesignState

logger = logging.getLogger(__name__)

# 常见违规模式（MVP 规则集，生产环境替换为 LLM + 标准库检索）
_VAGUE_NAMES = {"部件", "零件", "组件", "未知", "unknown", "part", "item"}


def load_standards_node(state: DesignState) -> dict[str, Any]:
    """MVP: 返回内置最小标准规则集，生产环境替换为知识库检索。"""
    standards = [
        {"id": "STD-001", "rule": "标号名称不得使用模糊词汇", "severity": "warning"},
        {"id": "STD-002", "rule": "装配图标号必须连续编号", "severity": "info"},
        {"id": "STD-003", "rule": "置信度<0.85的标号需人工确认", "severity": "warning"},
    ]
    return {"design_standards": standards}


def check_compliance_node(state: DesignState) -> dict[str, Any]:
    """对照标准检查标号合规性。"""
    labels    = state.get("labels") or []
    standards = state.get("design_standards") or []
    results   = []

    label_ids = [str(lbl.get("label_id", "")) for lbl in labels]
    # STD-002: 检查编号连续性（简化：检查是否从1开始连续）
    numeric_ids = sorted([int(lid) for lid in label_ids if lid.isdigit()])
    expected    = list(range(1, len(numeric_ids) + 1))
    id_gap      = numeric_ids != expected

    for lbl in labels:
        issues = []
        name = str(lbl.get("name", "")).strip()
        if name.lower() in _VAGUE_NAMES or not name:
            issues.append({"std": "STD-001", "detail": f"标号 {lbl.get('label_id')} 名称模糊: {name!r}"})
        if float(lbl.get("confidence", 1.0)) < 0.85:
            issues.append({"std": "STD-003", "detail": f"标号 {lbl.get('label_id')} 置信度偏低"})
        results.append({"label_id": lbl.get("label_id"), "issues": issues, "pass": len(issues) == 0})

    if id_gap:
        results.append({"label_id": "ALL", "issues": [{"std": "STD-002", "detail": f"编号不连续: {label_ids}"}], "pass": False})

    return {"compliance_results": results}


def generate_suggestions_node(state: DesignState) -> dict[str, Any]:
    """根据合规检查结果生成改进建议。"""
    suggestions = []
    for r in state.get("compliance_results") or []:
        for issue in r.get("issues") or []:
            suggestions.append(issue["detail"])
    return {"suggestions": suggestions}


def design_finalize_node(state: DesignState) -> dict[str, Any]:
    results     = state.get("compliance_results") or []
    suggestions = state.get("suggestions") or []
    pass_count  = sum(1 for r in results if r.get("pass"))
    total       = len(results)
    return {
        "final_result": {
            "pass_rate":   pass_count / total if total else 1.0,
            "issues":      [issue for r in results for issue in r.get("issues", [])],
            "suggestions": suggestions,
            "compliant":   all(r.get("pass") for r in results),
        }
    }
