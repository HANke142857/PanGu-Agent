"""Report Agent 节点（MVP：模板式报告生成）。"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from idmas.agents.report.state import ReportState


def collect_results_node(state: ReportState) -> dict[str, Any]:
    """收集各 Agent 结果，校验完整性。"""
    collected = {
        "vision":    bool(state.get("vision_result")),
        "design":    bool(state.get("design_result")),
        "process":   bool(state.get("process_result")),
        "knowledge": bool(state.get("knowledge_result")),
    }
    return {"report_sections": [{"name": "data_collection", "collected": collected}]}


def generate_sections_node(state: ReportState) -> dict[str, Any]:
    """为每个分析维度生成报告章节。"""
    sections = list(state.get("report_sections") or [])

    vision = state.get("vision_result") or {}
    if vision:
        labels = vision.get("labels") or []
        sections.append({
            "name":    "视觉识别",
            "content": f"共识别 {len(labels)} 个标号",
            "labels":  labels,
        })

    design = state.get("design_result") or {}
    if design:
        sections.append({
            "name":    "设计合规",
            "content": f"合规率 {design.get('pass_rate', 1.0):.0%}，"
                       f"发现 {len(design.get('issues', []))} 处问题",
            "issues":  design.get("issues", []),
        })

    process = state.get("process_result") or {}
    if process:
        sections.append({
            "name":     "工艺检查",
            "content":  f"工艺标号 {process.get('process_label_count', 0)} 个，"
                        f"{'全部正常' if process.get('all_ok') else '存在告警'}",
            "warnings": process.get("warnings", []),
        })

    knowledge = state.get("knowledge_result") or {}
    if knowledge:
        sections.append({
            "name":    "知识检索",
            "content": knowledge.get("rag_answer") or "无检索结果",
        })

    conflicts = state.get("conflicts_resolved") or []
    if conflicts:
        sections.append({
            "name":      "冲突解决",
            "content":   f"共 {len(conflicts)} 个冲突，已全部裁决",
            "conflicts": conflicts,
        })

    return {"report_sections": sections}


def generate_summary_node(state: ReportState) -> dict[str, Any]:
    """生成执行摘要。"""
    vision  = state.get("vision_result") or {}
    design  = state.get("design_result") or {}
    process = state.get("process_result") or {}

    label_count = len((vision.get("labels") or []))
    issues      = len((design.get("issues") or []))
    warnings    = len((process.get("warnings") or []))
    conflicts   = len(state.get("conflicts_resolved") or [])

    summary_lines = [
        f"识别标号：{label_count} 个",
        f"设计问题：{issues} 处" if issues else "设计合规：通过",
        f"工艺告警：{warnings} 条" if warnings else "工艺检查：通过",
    ]
    if conflicts:
        summary_lines.append(f"已解决冲突：{conflicts} 个")
    if state.get("human_decisions"):
        summary_lines.append("已完成人工审核")

    return {"summary": "  |  ".join(summary_lines)}


def format_report_node(state: ReportState) -> dict[str, Any]:
    """格式化最终报告（JSON + Markdown 摘要）。"""
    sections = state.get("report_sections") or []
    summary  = state.get("summary") or ""

    md_lines = ["# IDMAS 图纸解析报告", f"\n**摘要：** {summary}\n"]
    for sec in sections:
        name    = sec.get("name", "")
        content = sec.get("content", "")
        if name and content:
            md_lines.append(f"\n## {name}\n{content}")

    return {
        "final_report": {
            "summary":   summary,
            "sections":  sections,
            "markdown":  "\n".join(md_lines),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    }
