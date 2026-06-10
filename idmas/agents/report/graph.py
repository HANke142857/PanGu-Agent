"""Report SubGraph 构建。"""
from __future__ import annotations
from langgraph.graph import END, START, StateGraph
from idmas.agents.report.state import ReportState
from idmas.agents.report.nodes import (
    collect_results_node, generate_sections_node,
    generate_summary_node, format_report_node,
)


def build_report_graph():
    builder = StateGraph(ReportState)
    builder.add_node("collect_results",   collect_results_node)
    builder.add_node("generate_sections", generate_sections_node)
    builder.add_node("generate_summary",  generate_summary_node)
    builder.add_node("format_report",     format_report_node)
    builder.add_edge(START,               "collect_results")
    builder.add_edge("collect_results",   "generate_sections")
    builder.add_edge("generate_sections", "generate_summary")
    builder.add_edge("generate_summary",  "format_report")
    builder.add_edge("format_report",     END)
    return builder.compile()
