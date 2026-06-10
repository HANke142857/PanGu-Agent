"""
报告生成 Prompt 模板。

Report Agent 汇总各子 Agent 结果生成结构化报告。MVP 直接拼装；
接入 LLM 后用这些模板做自然语言润色与摘要。
"""
from __future__ import annotations

REPORT_SECTION_PROMPT = """根据以下「{section}」的解析结果，生成该章节的简洁说明（中文，要点式）：

{payload}
"""

REPORT_SUMMARY_PROMPT = """以下是图纸解析各章节内容，请提炼 3-5 条关键发现，生成执行摘要：

{sections}
"""

CONFLICT_RESOLUTION_PROMPT = """描述本次解析的冲突检测与裁决过程：

冲突项：
{conflicts}

用 2-3 句话说明冲突如何产生、如何裁决（自动/人工）。
"""


def build_section_prompt(section: str, payload: str) -> str:
    return REPORT_SECTION_PROMPT.format(section=section, payload=payload or "(无)")


def build_summary_prompt(sections: str) -> str:
    return REPORT_SUMMARY_PROMPT.format(sections=sections or "(无)")
