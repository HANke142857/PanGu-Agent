# =============================================================================
# Master Graph 条件路由函数
#
# 路由函数:
#   - route_by_intent(state: IDMASState) -> str
#     根据意图类型路由:
#       "vision_first" → 需要图纸视觉理解的任务
#       "knowledge_only" → 纯知识检索任务
#       "error" → 意图识别失败
#
#   - route_after_vision(state: IDMASState) -> str
#     Vision+OCR后的下一步路由:
#       "design" → 需要设计规范分析
#       "process" → 需要工艺参数校验
#       "knowledge" → 需要知识库辅助
#       "direct" → 直接进入冲突检测
#
#   - check_conflicts(state: IDMASState) -> str
#     冲突检查路由:
#       "has_conflict" → 检测到冲突，进入对抗辩论
#       "low_confidence" → 低置信度，需人工审核
#       "no_conflict" → 无冲突，直接生成报告
#
#   - check_debate(state: IDMASState) -> str
#     辩论结果路由:
#       "resolved" → 辩论裁决成功
#       "unresolved" → 辩论未解决，转人工仲裁
# =============================================================================
