# =============================================================================
# 领域层单元测试
#
# 测试:
#   - Drawing实体创建与校验
#   - DrawingLabel值对象
#   - AnalysisTask状态转换
#   - TaskType / TaskStatus / PromptMode 枚举
#   - ConflictInfo / DebateRound 值对象
#   - ImageDimension 校验 (>4096²拒绝)
#   - Confidence 阈值判断 (>=0.85高, <0.60低)
#   - 领域异常抛出
# =============================================================================
