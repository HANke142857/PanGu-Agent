"""
Master Graph 节点函数。
每个节点接收 IDMASState，返回部分状态更新 dict。

意图识别 / 对抗辩论支持 LLM 驱动（注入文本 chat_client，如 DeepSeek）；
未注入（chat_client=None）时退化为规则式，行为与 MVP 一致。
"""
from __future__ import annotations
import json
import logging
import re
import time
from typing import Any
from idmas.agents.master.state import IDMASState
from idmas.infrastructure.llm.vllm_client import BaseLLMClient, LLMMessage

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> dict[str, Any]:
    """从 LLM 回复中抽取 JSON（容忍 ```json 围栏与前后文本）。"""
    if not text:
        return {}
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except (json.JSONDecodeError, ValueError):
        return {}

# 意图 → 所需 Agent 映射
_INTENT_AGENTS: dict[str, list[str]] = {
    "label_recognition": ["vision"],
    "design_analysis":   ["vision", "design"],
    "process_check":     ["vision", "process"],
    "knowledge_query":   ["vision", "knowledge"],
    "comprehensive":     ["vision", "design", "process", "knowledge"],
}

_AUTO_RESOLVE_GAP       = 0.15
_AUTO_RESOLVE_THRESHOLD = 0.85


# ── 节点 1: intent_node ───────────────────────────────────────────────────

def intent_node(state: IDMASState) -> dict[str, Any]:
    """
    意图识别。MVP: 规则式（直接读 task_type）。
    生产环境替换为 LLM 语义分类。
    """
    task_type = state.get("task_type", "label_recognition")
    agents    = _INTENT_AGENTS.get(task_type, ["vision"])
    intent    = "knowledge_only" if task_type == "knowledge_query" else "vision_first"

    logger.info("[master] intent: task_type=%s → agents=%s", task_type, agents)
    return {
        "intent":          intent,
        "required_agents": agents,
        "status":          "processing",
        "messages":        [{"role": "system", "content": f"意图识别完成: {task_type}"}],
    }


def make_intent_node(chat_client: BaseLLMClient | None):
    """工厂：chat_client 为 None → 规则式；否则用 LLM 做语义意图分类（失败降级规则）。"""

    async def intent_node_llm(state: IDMASState) -> dict[str, Any]:
        if chat_client is None:
            return intent_node(state)

        from idmas.config.prompts.intent_prompts import INTENT_AGENT_MAP, build_intent_prompt

        question    = state.get("user_query") or ""
        has_drawing = bool(state.get("image_url"))
        try:
            prompt = build_intent_prompt(question, has_drawing)
            resp = await chat_client.chat_completion(
                [LLMMessage(role="user", content=prompt)], max_tokens=200, temperature=0.0)
            data = _extract_json(resp.content)
            intent_type = data.get("intent")
            if intent_type not in INTENT_AGENT_MAP:
                raise ValueError(f"未知意图: {intent_type!r}")
            agents = INTENT_AGENT_MAP[intent_type]
            intent = "knowledge_only" if intent_type == "knowledge_query" else "vision_first"
            logger.info("[master] intent(LLM): %s → %s", intent_type, agents)
            return {
                "intent":          intent,
                "required_agents": agents,
                "task_type":       intent_type,
                "status":          "processing",
                "messages":        [{"role": "system", "content": f"意图识别(LLM): {intent_type}"}],
            }
        except Exception as exc:  # noqa: BLE001 — 降级规则
            logger.warning("[master] intent LLM 失败，降级规则: %s", exc)
            return intent_node(state)

    return intent_node_llm


# ── 节点 2: preprocess_node ───────────────────────────────────────────────

def preprocess_node(state: IDMASState) -> dict[str, Any]:
    """基础校验：image_url 不能为空。"""
    image_url = state.get("image_url", "")
    if not image_url:
        return {"error": "image_url is required", "status": "failed"}
    logger.info("[master] preprocess: image_url=%s", image_url[:60])
    return {"messages": [{"role": "system", "content": "预处理完成"}]}


# ── 节点 3: vision_agent_node（异步工厂）────────────────────────────────────

async def make_vision_agent_node(llm_client: BaseLLMClient):
    """工厂函数：返回注入了 llm_client 的 Vision Agent 节点。"""
    async def vision_agent_node(state: IDMASState) -> dict[str, Any]:
        if state.get("error"):
            return {}
        from idmas.agents.vision.graph import build_vision_graph
        graph  = await build_vision_graph(llm_client)
        result = await graph.ainvoke({
            "image_url":   state.get("image_url", ""),
            "prompt_mode": state.get("prompt_mode", "standard_visual"),
        })
        final = result.get("final_result") or {}
        logger.info("[master] vision done: labels=%d", len(final.get("labels") or []))
        return {
            "vision_result": final,
            "messages":      [{"role": "agent", "content": f"Vision 完成，标号数={len(final.get('labels') or [])}"}],
        }
    return vision_agent_node


# ── 节点 4: design_agent_node ────────────────────────────────────────────

async def design_agent_node(state: IDMASState) -> dict[str, Any]:
    from idmas.agents.design.graph import build_design_graph
    vision  = state.get("vision_result") or {}
    labels  = vision.get("labels") or []
    graph   = build_design_graph()
    result  = await graph.ainvoke({"labels": labels, "drawing_type": "assembly"})
    final   = result.get("final_result") or {}
    logger.info("[master] design done: compliant=%s", final.get("compliant"))
    return {
        "design_result": final,
        "messages":      [{"role": "agent", "content": f"Design 完成，合规={final.get('compliant')}"}],
    }


# ── 节点 5: process_agent_node ───────────────────────────────────────────

async def process_agent_node(state: IDMASState) -> dict[str, Any]:
    from idmas.agents.process.graph import build_process_graph
    vision = state.get("vision_result") or {}
    labels = vision.get("labels") or []
    graph  = build_process_graph()
    result = await graph.ainvoke({"labels": labels})
    final  = result.get("final_result") or {}
    logger.info("[master] process done: all_ok=%s", final.get("all_ok"))
    return {
        "process_result": final,
        "messages":       [{"role": "agent", "content": "Process 完成"}],
    }


# ── 节点 6: knowledge_agent_node ─────────────────────────────────────────

async def knowledge_agent_node(state: IDMASState) -> dict[str, Any]:
    from idmas.agents.knowledge.graph import build_knowledge_graph
    vision = state.get("vision_result") or {}
    labels = vision.get("labels") or []
    query  = state.get("user_query") or "识别图纸中的部件"
    graph  = build_knowledge_graph()
    result = await graph.ainvoke({"query": query, "labels": labels})
    final  = result.get("final_result") or {}
    logger.info("[master] knowledge done: source_count=%s", final.get("source_count"))
    return {
        "knowledge_result": final,
        "messages":         [{"role": "agent", "content": "Knowledge 完成"}],
    }


# ── 节点 7: conflict_detection_node ──────────────────────────────────────

def conflict_detection_node(state: IDMASState) -> dict[str, Any]:
    """
    比对 Vision 与 Knowledge 的标号识别结果。
    置信度差距 > 15% 且高方 > 85% → 可尝试自动裁决（交给辩论节点）。
    """
    vision    = state.get("vision_result") or {}
    knowledge = state.get("knowledge_result") or {}
    v_labels  = {l["label_id"]: l for l in (vision.get("labels") or [])}
    k_labels  = {}  # MVP: knowledge 无标号级结果，跳过比对

    conflicts: list[dict[str, Any]] = []
    # 真实冲突检测：双方都有同一标号但命名不同时触发
    for lid, v_lbl in v_labels.items():
        k_lbl = k_labels.get(lid)
        if k_lbl and v_lbl.get("name") != k_lbl.get("name"):
            conflicts.append({
                "label_id":            lid,
                "vision_name":         v_lbl.get("name"),
                "knowledge_name":      k_lbl.get("name"),
                "vision_confidence":   v_lbl.get("confidence", 0),
                "knowledge_confidence": k_lbl.get("confidence", 0),
                "resolution":          None,
            })

    # 提前判断是否需要人工审核（路由函数 check_conflicts 会据此决定）
    vision = state.get("vision_result") or {}
    labels = vision.get("labels") or []
    low_conf_labels   = [l for l in labels if l.get("needs_review")]
    human_needed      = bool(low_conf_labels) or bool(conflicts)
    pre_status        = "waiting_review" if human_needed else "processing"

    logger.info("[master] conflict_detection: %d conflicts, %d low-conf, human_needed=%s",
                len(conflicts), len(low_conf_labels), human_needed)
    return {
        "conflicts":          conflicts,
        "human_review_needed": human_needed,
        "status":             pre_status,
        "messages":  [{"role": "system", "content": f"冲突检测完成: {len(conflicts)} 个冲突"}],
    }


# ── 节点 8: adversarial_debate_node ──────────────────────────────────────

def adversarial_debate_node(state: IDMASState) -> dict[str, Any]:
    """
    对抗辩论节点（MVP：规则式自动裁决）。
    规则：置信度高方 > 85% 且差距 > 15% → 高方获胜。
    生产环境替换为 LLM 多轮辩论。
    """
    conflicts     = list(state.get("conflicts") or [])
    rounds:  list[dict[str, Any]] = []
    all_resolved  = True

    for i, c in enumerate(conflicts):
        v_conf = c.get("vision_confidence", 0)
        k_conf = c.get("knowledge_confidence", 0)
        high   = max(v_conf, k_conf)
        gap    = abs(v_conf - k_conf)

        if high >= _AUTO_RESOLVE_THRESHOLD and gap >= _AUTO_RESOLVE_GAP:
            winner      = "vision" if v_conf >= k_conf else "knowledge"
            resolution  = c["vision_name"] if winner == "vision" else c["knowledge_name"]
            conflicts[i] = {**c, "resolution": resolution, "resolved_by": "auto"}
            rounds.append({
                "round": i + 1, "label_id": c["label_id"],
                "winner": winner, "resolution": resolution,
            })
        else:
            all_resolved = False
            rounds.append({"round": i + 1, "label_id": c["label_id"], "winner": None})

    logger.info("[master] debate: resolved=%s", all_resolved)
    return {
        "conflicts":       conflicts,
        "debate_rounds":   rounds,
        "debate_resolved": all_resolved,
        "messages":        [{"role": "system", "content": f"辩论完成: resolved={all_resolved}"}],
    }


def make_debate_node(chat_client: BaseLLMClient | None):
    """工厂：先跑规则裁决；chat_client 存在时，对规则未决的冲突再用 LLM 裁判（失败保留规则结果）。"""

    async def debate_node_llm(state: IDMASState) -> dict[str, Any]:
        base = adversarial_debate_node(state)            # 规则裁决
        if chat_client is None:
            return base

        from idmas.config.prompts.debate_prompts import build_judge_prompt

        conflicts = list(base.get("conflicts") or [])
        if all(c.get("resolution") for c in conflicts):
            return base

        for c in conflicts:
            if c.get("resolution"):
                continue
            try:
                prompt = build_judge_prompt(
                    c.get("vision_name", ""), c.get("vision_confidence", 0.0),
                    c.get("knowledge_name", ""), c.get("knowledge_confidence", 0.0))
                resp = await chat_client.chat_completion(
                    [LLMMessage(role="user", content=prompt)], max_tokens=200, temperature=0.0)
                data = _extract_json(resp.content)
                winner = data.get("winner")
                if winner == "vision":
                    c["resolution"], c["resolved_by"] = c.get("vision_name"), "llm"
                elif winner == "knowledge":
                    c["resolution"], c["resolved_by"] = c.get("knowledge_name"), "llm"
            except Exception as exc:  # noqa: BLE001 — 保留规则结果
                logger.warning("[master] debate LLM 失败: %s", exc)

        base["conflicts"] = conflicts
        base["debate_resolved"] = all(c.get("resolution") for c in conflicts)
        logger.info("[master] debate(LLM): resolved=%s", base["debate_resolved"])
        return base

    return debate_node_llm


# ── 节点 9: human_review_node ─────────────────────────────────────────────

def human_review_node(state: IDMASState) -> dict[str, Any]:
    """
    人工审核节点。
    LangGraph 在此节点前中断（interrupt_before），等待外部输入后恢复。

    执行时机：
    - 首次触发：graph 在此节点前中断，此函数NOT被调用；status 由 conflict_detection 设为 waiting_review
    - 恢复执行：此函数被调用，检查 human_decision 是否已注入
      - 已注入 → 标记完成，继续后续流程
      - 未注入 → 异常情况，保持 waiting_review
    """
    if state.get("human_decision"):
        logger.info("[master] human_review: decision received, resuming...")
        return {
            "status":              "completed",
            "human_review_needed": False,
            "messages":            [{"role": "system", "content": "人工审核完成，继续生成报告"}],
        }
    # 异常路径（理论上不应到达）
    logger.warning("[master] human_review: no decision found, staying in review")
    return {
        "status":              "waiting_review",
        "human_review_needed": True,
        "messages":            [{"role": "system", "content": "等待人工审核"}],
    }


# ── 节点 10: report_agent_node ────────────────────────────────────────────

async def report_agent_node(state: IDMASState) -> dict[str, Any]:
    from idmas.agents.report.graph import build_report_graph
    resolved_conflicts = [c for c in (state.get("conflicts") or []) if c.get("resolution")]
    graph  = build_report_graph()
    result = await graph.ainvoke({
        "vision_result":      state.get("vision_result"),
        "design_result":      state.get("design_result"),
        "process_result":     state.get("process_result"),
        "knowledge_result":   state.get("knowledge_result"),
        "conflicts_resolved": resolved_conflicts,
        "human_decisions":    state.get("human_decision"),
    })
    final = result.get("final_report") or {}
    logger.info("[master] report done")
    return {
        "report_result": final,
        "messages":      [{"role": "agent", "content": "报告生成完成"}],
    }


# ── 节点 11: aggregation_node ────────────────────────────────────────────

def aggregation_node(state: IDMASState) -> dict[str, Any]:
    """结果聚合：统计 token、标记完成状态。"""
    vision  = state.get("vision_result") or {}
    labels  = vision.get("labels") or []
    review_needed = any(l.get("needs_review") for l in labels) or bool(state.get("conflicts"))
    status  = "waiting_review" if state.get("human_review_needed") else "completed"
    logger.info("[master] aggregation: status=%s, labels=%d", status, len(labels))
    return {
        "status":   status,
        "messages": [{"role": "system", "content": f"聚合完成: {len(labels)} 个标号"}],
    }


# ── 节点 12: error_handler_node ──────────────────────────────────────────

def error_handler_node(state: IDMASState) -> dict[str, Any]:
    error = state.get("error") or "Unknown error"
    logger.error("[master] error_handler: %s", error)
    return {
        "status":   "failed",
        "messages": [{"role": "system", "content": f"错误: {error}"}],
    }
