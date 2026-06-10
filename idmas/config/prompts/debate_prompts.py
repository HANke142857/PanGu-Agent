"""
对抗辩论 Prompt 模板。

当 Vision 与 Knowledge 对同一标号判断不一致时，Master 主持多轮辩论：
请双方各自给证据 → 互相反驳 → 裁判加权裁决。
裁决规则：置信度差距 > 15% 且高方 > 85% → 自动裁决，否则转人工。
"""
from __future__ import annotations

EVIDENCE_REQUEST_PROMPT = """针对图纸标号「{label_id}」，你判断它是「{claim}」。
请给出支持该判断的证据（图形特征、空间位置、行业惯例等），简明 3 条以内。
"""

REBUTTAL_REQUEST_PROMPT = """对方对标号「{label_id}」的判断是「{opponent_claim}」，证据如下：
{opponent_evidence}

请指出其证据的薄弱处，并重申你的判断「{claim}」。
"""

JUDGE_PROMPT = """你是标号识别争议的裁判。两方判断：
- Vision：{vision_name}（置信度 {vision_conf:.2f}）
- Knowledge：{knowledge_name}（置信度 {knowledge_conf:.2f}）

双方证据/反驳：
{transcript}

裁决规则：置信度差距 > 0.15 且高方 > 0.85 → 采纳高方；否则判定需人工仲裁。
只输出 JSON：{{"winner": "vision|knowledge|human", "name": "<最终名称或空>", "reason": "<一句话>"}}
"""


def build_judge_prompt(
    vision_name: str, vision_conf: float,
    knowledge_name: str, knowledge_conf: float,
    transcript: str = "",
) -> str:
    return JUDGE_PROMPT.format(
        vision_name=vision_name, vision_conf=vision_conf,
        knowledge_name=knowledge_name, knowledge_conf=knowledge_conf,
        transcript=transcript or "(无)",
    )


def auto_resolve(vision_conf: float, knowledge_conf: float,
                 high_threshold: float = 0.85, gap_threshold: float = 0.15) -> str | None:
    """规则裁决：返回 'vision'/'knowledge'，无法自动裁决返回 None（转人工）。"""
    gap = abs(vision_conf - knowledge_conf)
    if gap <= gap_threshold:
        return None
    winner_conf = max(vision_conf, knowledge_conf)
    if winner_conf < high_threshold:
        return None
    return "vision" if vision_conf > knowledge_conf else "knowledge"
