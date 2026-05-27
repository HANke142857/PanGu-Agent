# =============================================================================
# PaddleOCR 客户端
#
# 职责:
#   - 封装PaddleOCR服务API调用
#   - 提取图纸中的文字、坐标、置信度
#   - 支持中英文混合识别
#
# 配置:
#   - OCR_URL: PaddleOCR服务地址 (默认 http://localhost:8100)
#   - OCR_TIMEOUT: 超时时间 (30s)
#
# 方法:
#   - extract(image_url: str) -> OCRResult
#     返回: {texts: list[str], boxes: list[list[int]], scores: list[float]}
#   - extract_labels(image_url: str) -> list[LabelOCR]
#     提取标号相关的文字和坐标
#   - health_check() -> bool
# =============================================================================
