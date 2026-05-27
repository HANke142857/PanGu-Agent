# =============================================================================
# Vision SubGraph 构建
#
# 节点:
#   - preprocess_image: 图片预处理(缩放、格式转换)
#   - build_prompt: 根据prompt_mode构建推理Prompt
#   - vllm_inference: 调用vLLM进行视觉推理
#   - parse_output: 解析VLM输出为结构化标号列表
#   - confidence_check: 置信度检查
#   - ocr_retry: OCR辅助重试(低置信度时用OCR补充)
#   - finalize: 输出最终结果
#
# 流程:
#   preprocess_image → build_prompt → vllm_inference → parse_output
#   → confidence_check → [retry: ocr_retry → vllm_inference] / [done: finalize]
#
# 重试策略: needs_ocr_retry && retry_count < 1 → 重试
# =============================================================================
