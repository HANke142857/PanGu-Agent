"""Design SubGraph 构建。"""
from __future__ import annotations
from langgraph.graph import END, START, StateGraph
from idmas.agents.design.state import DesignState
from idmas.agents.design.nodes import (
    load_standards_node, check_compliance_node,
    generate_suggestions_node, design_finalize_node,
)


def build_design_graph():
    builder = StateGraph(DesignState)
    builder.add_node("load_standards",       load_standards_node)
    builder.add_node("check_compliance",     check_compliance_node)
    builder.add_node("generate_suggestions", generate_suggestions_node)
    builder.add_node("finalize",             design_finalize_node)
    builder.add_edge(START,                  "load_standards")
    builder.add_edge("load_standards",       "check_compliance")
    builder.add_edge("check_compliance",     "generate_suggestions")
    builder.add_edge("generate_suggestions", "finalize")
    builder.add_edge("finalize",             END)
    return builder.compile()
