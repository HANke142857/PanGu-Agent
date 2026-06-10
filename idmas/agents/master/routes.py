"""
Master Graph 条件路由函数。
每个函数接收 IDMASState，返回下一节点名称字符串。
"""
from __future__ import annotations
from idmas.agents.master.state import IDMASState

# 冲突自动裁决规则：置信度差距 > 15% 且高方 > 85%
_AUTO_RESOLVE_GAP       = 0.15
_AUTO_RESOLVE_THRESHOLD = 0.85


def route_by_intent(state: IDMASState) -> str:
    """意图识别后路由。"""
    if state.get("error"):
        return "error_handler"
    intent = state.get("intent", "vision_first")
    if intent == "knowledge_only":
        return "knowledge_agent"
    return "vision_agent"   # 默认走 Vision 优先


def route_after_vision(state: IDMASState) -> str:
    """Vision 完成后，按 required_agents 决定下一步。"""
    if state.get("error"):
        return "error_handler"
    agents = state.get("required_agents") or []
    if "design" in agents:
        return "design_agent"
    if "process" in agents:
        return "process_agent"
    if "knowledge" in agents:
        return "knowledge_agent"
    return "conflict_detection"


def route_after_design(state: IDMASState) -> str:
    """Design 完成后路由。"""
    agents = state.get("required_agents") or []
    if "process" in agents:
        return "process_agent"
    if "knowledge" in agents:
        return "knowledge_agent"
    return "conflict_detection"


def route_after_process(state: IDMASState) -> str:
    """Process 完成后路由。"""
    agents = state.get("required_agents") or []
    if "knowledge" in agents:
        return "knowledge_agent"
    return "conflict_detection"


def check_conflicts(state: IDMASState) -> str:
    """冲突检查后路由。"""
    conflicts = state.get("conflicts") or []
    if not conflicts:
        # 检查是否有低置信度标号需要人工
        vision = state.get("vision_result") or {}
        labels = vision.get("labels") or []
        low_conf = [l for l in labels if l.get("needs_review")]
        if low_conf:
            return "low_confidence"
        return "no_conflict"

    # 判断冲突是否可自动裁决
    for c in conflicts:
        high = max(c.get("vision_confidence", 0), c.get("knowledge_confidence", 0))
        low  = min(c.get("vision_confidence", 0), c.get("knowledge_confidence", 0))
        gap  = high - low
        if gap <= _AUTO_RESOLVE_GAP or high <= _AUTO_RESOLVE_THRESHOLD:
            return "has_conflict"   # 需要辩论裁决
    return "has_conflict"


def check_debate(state: IDMASState) -> str:
    """辩论结果路由。"""
    if state.get("debate_resolved"):
        return "resolved"
    return "unresolved"   # 辩论未解决 → 人工仲裁
