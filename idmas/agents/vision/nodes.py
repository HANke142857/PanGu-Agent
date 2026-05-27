# =============================================================================
# Vision SubGraph 节点函数
#
# 节点函数:
#   - preprocess_image_node(state: VisionState) -> dict
#     图片预处理: 尺寸检查、格式转换、缩放(如需要)
#
#   - build_prompt_node(state: VisionState) -> dict
#     根据prompt_mode从Jinja2模板构建Prompt
#     支持: standard_visual / cot_visual / few_shot_visual
#
#   - vllm_inference_node(state: VisionState) -> dict
#     调用vLLM Vision API进行图纸推理
#     模型: qwen2.5-vl-7b-finetuned
#     参数: max_tokens=2048, temperature=0.1
#
#   - parse_output_node(state: VisionState) -> dict
#     解析VLM输出文本为结构化标号列表
#     提取: label_id, name, confidence, spatial_info
#
#   - confidence_check_node(state: VisionState) -> dict
#     检查各标号置信度，标记低置信度标号
#     阈值: < 0.60 需要OCR辅助
#
#   - ocr_retry_node(state: VisionState) -> dict
#     调用PaddleOCR获取文字坐标，融合OCR结果补充Prompt后重试
#
#   - finalize_node(state: VisionState) -> dict
#     汇总最终结果，格式化输出
# =============================================================================
