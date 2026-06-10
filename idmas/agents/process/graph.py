"""Process SubGraph 构建。"""
from __future__ import annotations
from langgraph.graph import END, START, StateGraph
from idmas.agents.process.state import ProcessState
from idmas.agents.process.nodes import (
    extract_params_node, check_params_node,
    check_sequence_node, process_finalize_node,
)


def build_process_graph():
    builder = StateGraph(ProcessState)
    builder.add_node("extract_params",  extract_params_node)
    builder.add_node("check_params",    check_params_node)
    builder.add_node("check_sequence",  check_sequence_node)
    builder.add_node("finalize",        process_finalize_node)
    builder.add_edge(START,             "extract_params")
    builder.add_edge("extract_params",  "check_params")
    builder.add_edge("check_params",    "check_sequence")
    builder.add_edge("check_sequence",  "finalize")
    builder.add_edge("finalize",        END)
    return builder.compile()
