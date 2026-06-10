"""
意图识别 Prompt 模板。

供 Master Agent 在 LLM 模式下识别用户意图、决定调用哪些子 Agent。
（MVP 默认走规则式路由；接入真实 LLM 后用这些模板。）
"""
from __future__ import annotations

# 意图类型 → 需要调用的 Agent 链
INTENT_AGENT_MAP: dict[str, list[str]] = {
    "label_recognition": ["vision"],
    "design_analysis":   ["vision", "design"],
    "process_check":     ["vision", "process"],
    "knowledge_query":   ["vision", "knowledge"],
    "comprehensive":     ["vision", "design", "process", "knowledge"],
}

INTENT_RECOGNITION_PROMPT = """你是工业图纸解析系统的意图识别器。
根据用户提问和是否提供图纸，判断意图类型，并给出需要调用的 Agent 列表。

可选意图类型（只能选其一）：
- label_recognition：识别图纸上的标号
- design_analysis：设计规范/命名合规分析
- process_check：工艺参数校验
- knowledge_query：知识检索问答
- comprehensive：综合分析（全链路）

只输出 JSON：{{"intent": "<类型>", "agents": ["vision", ...]}}

是否有图纸：{has_drawing}
用户提问：{question}
"""


def build_intent_prompt(question: str, has_drawing: bool) -> str:
    return INTENT_RECOGNITION_PROMPT.format(
        has_drawing="是" if has_drawing else "否",
        question=question or "(无)",
    )


def agents_for_intent(intent: str) -> list[str]:
    """意图 → Agent 链（未知意图退化为标号识别）。"""
    return INTENT_AGENT_MAP.get(intent, INTENT_AGENT_MAP["label_recognition"])
