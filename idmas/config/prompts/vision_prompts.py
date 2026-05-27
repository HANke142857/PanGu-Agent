# =============================================================================
# Vision Agent Prompt模板
#
# 模板:
#   - STANDARD_VISUAL_PROMPT: 标准视觉提示
#     直接要求模型识别图纸中所有标号及其名称
#
#   - COT_VISUAL_PROMPT: 思维链(Chain-of-Thought)视觉提示
#     引导模型分步推理:
#     1. 先识别图纸类型
#     2. 识别图中所有标号位置
#     3. 逐个分析标号含义
#     4. 给出最终结构化结果
#
#   - FEW_SHOT_VISUAL_PROMPT: 少样本视觉提示
#     包含示例输入输出，引导模型理解输出格式
#
#   - OCR_AUGMENTED_PROMPT: OCR增强提示
#     在标准提示基础上，附加OCR提取的文字坐标信息
#
# 输出格式要求:
#   JSON格式，包含labels数组，每个label含:
#   label_id, name, confidence, spatial_description
# =============================================================================
