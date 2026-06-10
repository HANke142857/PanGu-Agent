"""
Vision Agent Prompt 模板。

所有 Prompt 要求模型输出严格 JSON，无额外文本——
这是防幻觉的第一道防线：parse_output_node 用 json.loads() 校验，
解析失败即视为推理失败，触发重试。
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 标准视觉 Prompt
# ---------------------------------------------------------------------------

STANDARD_VISUAL_PROMPT = """\
你是一位工业图纸标号识别专家。请仔细观察图纸，识别图中所有数字标号（如①②③或1、2、3等），\
并分析每个标号所指部件的名称和位置。

【输出要求】
严格输出 JSON 格式，不要有任何额外说明文字：
{
  "labels": [
    {
      "label_id": "标号编号（字符串）",
      "name": "部件名称",
      "confidence": 置信度（0.0~1.0的浮点数）,
      "spatial_description": "标号在图纸中的位置描述",
      "bounding_box": {
        "x": 左上角x坐标（归一化0~1）,
        "y": 左上角y坐标（归一化0~1）,
        "width": 宽度（归一化0~1）,
        "height": 高度（归一化0~1）
      }
    }
  ]
}
"""

# ---------------------------------------------------------------------------
# CoT（思维链）视觉 Prompt
# ---------------------------------------------------------------------------

COT_VISUAL_PROMPT = """\
你是一位工业图纸标号识别专家。请按以下步骤分析图纸，最后给出 JSON 结果。

【分析步骤】
第一步：判断图纸类型（装配图/零件图/工艺图/原理图/专利图）
第二步：找出图中所有数字标号的位置（通常为圆圈数字或引线标注）
第三步：逐一分析每个标号所指部件的名称和功能
第四步：评估每个识别结果的置信度（依据图纸清晰度、标号歧义性判断）

【输出要求】
请先输出思考过程（cot_steps），再输出最终 JSON 结果：
{
  "cot_steps": [
    {"step": 1, "result": "图纸类型描述"},
    {"step": 2, "result": "标号位置描述"},
    {"step": 3, "result": "各标号分析"},
    {"step": 4, "result": "置信度评估"}
  ],
  "labels": [
    {
      "label_id": "标号编号",
      "name": "部件名称",
      "confidence": 置信度,
      "spatial_description": "位置描述",
      "bounding_box": {"x": 0.0, "y": 0.0, "width": 0.1, "height": 0.1}
    }
  ]
}
"""

# ---------------------------------------------------------------------------
# Few-Shot 视觉 Prompt
# ---------------------------------------------------------------------------

FEW_SHOT_VISUAL_PROMPT = """\
你是一位工业图纸标号识别专家。以下是输入输出示例，请按同样格式分析当前图纸。

【示例】
输入：一张齿轮箱装配图，图中有标号1、2、3
输出：
{
  "labels": [
    {"label_id": "1", "name": "轴承座", "confidence": 0.92,
     "spatial_description": "左上方传动轴支撑处",
     "bounding_box": {"x": 0.05, "y": 0.05, "width": 0.15, "height": 0.12}},
    {"label_id": "2", "name": "齿轮箱体", "confidence": 0.88,
     "spatial_description": "图纸中央主体",
     "bounding_box": {"x": 0.35, "y": 0.30, "width": 0.30, "height": 0.35}},
    {"label_id": "3", "name": "输出轴", "confidence": 0.85,
     "spatial_description": "右侧输出端",
     "bounding_box": {"x": 0.75, "y": 0.40, "width": 0.18, "height": 0.10}}
  ]
}

【当前任务】
请用相同格式识别当前图纸中的所有标号，严格输出 JSON，不要额外说明。
"""

# ---------------------------------------------------------------------------
# OCR 增强 Prompt（低置信度重试时使用）
# ---------------------------------------------------------------------------

OCR_AUGMENTED_PROMPT_TEMPLATE = """\
你是一位工业图纸标号识别专家。OCR 已从图纸中提取了以下文字及坐标信息，请结合图像视觉内容和 OCR 结果，\
重新识别所有标号。

【OCR 提取结果】
{ocr_results}

【任务要求】
1. 优先以视觉判断为准，OCR 信息作为辅助参考
2. 如 OCR 文字明显为标号（纯数字或数字+字母），请提高对应标号的置信度
3. 严格输出 JSON，格式同下：
{{
  "labels": [
    {{
      "label_id": "标号编号",
      "name": "部件名称",
      "confidence": 置信度,
      "spatial_description": "位置描述",
      "bounding_box": {{"x": 0.0, "y": 0.0, "width": 0.1, "height": 0.1}}
    }}
  ]
}}
"""


def build_ocr_augmented_prompt(ocr_results: list[dict]) -> str:
    """将 OCR 结果格式化后注入 Prompt 模板。"""
    lines = []
    for item in ocr_results:
        text  = item.get("text", "")
        score = item.get("score", 0.0)
        box   = item.get("box", [])
        lines.append(f"  文字: {text!r}  置信度: {score:.2f}  位置: {box}")
    ocr_str = "\n".join(lines) if lines else "  （无 OCR 结果）"
    return OCR_AUGMENTED_PROMPT_TEMPLATE.format(ocr_results=ocr_str)


# Prompt 模式映射表（供 build_prompt_node 查找）
PROMPT_MAP: dict[str, str] = {
    "standard_visual": STANDARD_VISUAL_PROMPT,
    "cot_visual":      COT_VISUAL_PROMPT,
    "few_shot_visual": FEW_SHOT_VISUAL_PROMPT,
}
