# =============================================================================
# Vision SubGraph 状态定义 (VisionState)
#
# 状态字段:
#   - image_url: str                  # 图纸URL
#   - prompt_mode: str                # Prompt模式
#   - cot_steps: list[dict]           # CoT推理步骤
#   - parsed_labels: list[dict] | None # 解析出的标号列表
#   - confidence_scores: dict | None  # 各标号置信度
#   - needs_ocr_retry: bool           # 是否需要OCR辅助重试
#   - retry_count: int                # 当前重试次数 (上限1次)
#   - final_result: dict | None       # 最终结果
# =============================================================================
