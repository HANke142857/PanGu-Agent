# =============================================================================
# 领域异常定义
#
# 基础异常:
#   - IDMASError: 系统基础异常
#   - DomainError: 领域逻辑错误
#
# 具体异常:
#   - DrawingNotFoundError: 图纸不存在
#   - TaskNotFoundError: 任务不存在
#   - InvalidDrawingError: 图纸校验失败 (如尺寸超限 >4096²)
#   - InvalidTaskStateError: 非法任务状态转换
#   - ConflictDetectedError: 检测到标号冲突
#   - LowConfidenceError: 置信度低于阈值
#   - PLMConnectionError: PLM系统连接失败
#   - VLLMInferenceError: vLLM推理失败
#   - OCRExtractionError: OCR提取失败
#   - KnowledgeSearchError: 知识检索失败
#   - AuthenticationError: 认证失败
#   - AuthorizationError: 权限不足
#   - RateLimitExceededError: 频率超限
#
# 错误码映射: 参见技术设计文档 2.3节 错误码规范
#   IDMAS-{HTTP状态码}-{序号}
# =============================================================================
