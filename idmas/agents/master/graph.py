"""
Master Graph — 多 Agent 协同主编排图。

完整流程::

    START → intent → preprocess
      → [route_by_intent]
          ├─ vision_agent → [route_after_vision]
          │     ├─ design_agent  → [route_after_design]
          │     │     ├─ process_agent → [route_after_process]
          │     │     │     ├─ knowledge_agent → conflict_detection
          │     │     │     └─ conflict_detection
          │     │     ├─ knowledge_agent → conflict_detection
          │     │     └─ conflict_detection
          │     ├─ process_agent → ...
          │     ├─ knowledge_agent → conflict_detection
          │     └─ conflict_detection
          └─ knowledge_agent → conflict_detection
      → [check_conflicts]
          ├─ has_conflict   → adversarial_debate → [check_debate]
          │                       ├─ resolved   → report_agent
          │                       └─ unresolved → human_review → report_agent
          ├─ low_confidence → human_review → report_agent
          └─ no_conflict    → report_agent
      → aggregation → END

中断点: interrupt_before=["human_review"]
Checkpointer: MemorySaver (MVP)，生产替换为 Redis/PostgreSQL Checkpointer

使用方法::

    graph, checkpointer = await build_master_graph(FakeVLLMClient())

    # 首次执行
    config = {"configurable": {"thread_id": "task-uuid-xxx"}}
    result = await graph.ainvoke(initial_state, config=config)

    # 若 status == "waiting_review"，人工输入后恢复
    await graph.aupdate_state(config, {"human_decision": {...}})
    result = await graph.ainvoke(None, config=config)
"""
from __future__ import annotations
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from idmas.agents.master.nodes import (
    intent_node,
    preprocess_node,
    make_vision_agent_node,
    design_agent_node,
    process_agent_node,
    knowledge_agent_node,
    conflict_detection_node,
    adversarial_debate_node,
    human_review_node,
    report_agent_node,
    aggregation_node,
    error_handler_node,
)
from idmas.agents.master.routes import (
    route_by_intent,
    route_after_vision,
    route_after_design,
    route_after_process,
    check_conflicts,
    check_debate,
)
from idmas.agents.master.state import IDMASState
from idmas.infrastructure.llm.vllm_client import BaseLLMClient


async def build_master_graph(
    llm_client:  BaseLLMClient,
    checkpointer: Any | None = None,
    enable_human_review: bool = True,
):
    """
    构建并编译 Master Graph。

    Args:
        llm_client:          LLM 推理客户端
        checkpointer:        LangGraph Checkpointer（None → MemorySaver）
        enable_human_review: 是否启用人工审核中断（False 用于测试快速跑通）

    Returns:
        (compiled_graph, checkpointer) — checkpointer 需要传给调用方用于状态恢复
    """
    # 依赖注入的 Vision 节点
    vision_node = await make_vision_agent_node(llm_client)

    # Checkpointer（仅在启用 human_review 时才需要持久化状态）
    cp = (checkpointer or MemorySaver()) if enable_human_review else None

    builder = StateGraph(IDMASState)

    # ── 注册所有节点 ────────────────────────────────────────────────
    builder.add_node("intent",              intent_node)
    builder.add_node("preprocess",          preprocess_node)
    builder.add_node("vision_agent",        vision_node)
    builder.add_node("design_agent",        design_agent_node)
    builder.add_node("process_agent",       process_agent_node)
    builder.add_node("knowledge_agent",     knowledge_agent_node)
    builder.add_node("conflict_detection",  conflict_detection_node)
    builder.add_node("adversarial_debate",  adversarial_debate_node)
    builder.add_node("human_review",        human_review_node)
    builder.add_node("report_agent",        report_agent_node)
    builder.add_node("aggregation",         aggregation_node)
    builder.add_node("error_handler",       error_handler_node)

    # ── 固定边 ──────────────────────────────────────────────────────
    builder.add_edge(START,                "intent")
    builder.add_edge("intent",             "preprocess")

    # preprocess → route_by_intent
    builder.add_conditional_edges(
        "preprocess",
        route_by_intent,
        {"vision_agent": "vision_agent", "knowledge_agent": "knowledge_agent", "error_handler": "error_handler"},
    )

    # vision → route_after_vision
    builder.add_conditional_edges(
        "vision_agent",
        route_after_vision,
        {
            "design_agent":      "design_agent",
            "process_agent":     "process_agent",
            "knowledge_agent":   "knowledge_agent",
            "conflict_detection":"conflict_detection",
            "error_handler":     "error_handler",
        },
    )

    # design → route_after_design
    builder.add_conditional_edges(
        "design_agent",
        route_after_design,
        {
            "process_agent":      "process_agent",
            "knowledge_agent":    "knowledge_agent",
            "conflict_detection": "conflict_detection",
        },
    )

    # process → route_after_process
    builder.add_conditional_edges(
        "process_agent",
        route_after_process,
        {
            "knowledge_agent":    "knowledge_agent",
            "conflict_detection": "conflict_detection",
        },
    )

    # knowledge → conflict_detection（knowledge 后固定进入冲突检测）
    builder.add_edge("knowledge_agent", "conflict_detection")

    # conflict_detection → check_conflicts
    builder.add_conditional_edges(
        "conflict_detection",
        check_conflicts,
        {
            "has_conflict":   "adversarial_debate",
            "low_confidence": "human_review",
            "no_conflict":    "report_agent",
        },
    )

    # adversarial_debate → check_debate
    builder.add_conditional_edges(
        "adversarial_debate",
        check_debate,
        {
            "resolved":   "report_agent",
            "unresolved": "human_review",
        },
    )

    # human_review → report（审核完成后继续生成报告）
    builder.add_edge("human_review",   "report_agent")

    # report → aggregation → END
    builder.add_edge("report_agent",   "aggregation")
    builder.add_edge("aggregation",    END)
    builder.add_edge("error_handler",  END)

    # ── 编译（含中断点 + Checkpointer）────────────────────────────
    interrupt_before = ["human_review"] if enable_human_review else []
    compile_kwargs: dict[str, Any] = {"interrupt_before": interrupt_before}
    if cp is not None:
        compile_kwargs["checkpointer"] = cp

    graph = builder.compile(**compile_kwargs)
    return graph, cp
