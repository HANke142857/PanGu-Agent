# =============================================================================
# 解析任务领域值对象
#
# 包含:
#   - TaskType: 任务类型枚举
#     (label_recognition/design_analysis/process_check/knowledge_query/comprehensive)
#   - TaskStatus: 任务状态枚举
#     (created/processing/waiting_review/completed/failed)
#   - PromptMode: Prompt模式枚举
#     (standard_visual/cot_visual/few_shot_visual)
#   - ReviewAction: 审核动作枚举 (confirm/correct/reject)
#   - ConflictInfo: 冲突信息值对象
#     - label_id: 标号ID
#     - vision_name: Vision Agent识别名称
#     - knowledge_name: Knowledge Agent名称
#     - vision_confidence: Vision置信度
#     - knowledge_confidence: Knowledge置信度
#     - resolution: 裁决结果
#   - DebateRound: 辩论轮次值对象
#     - round_number: 轮次
#     - vision_evidence: Vision证据
#     - knowledge_evidence: Knowledge证据
#     - judge_result: 裁判结果
# =============================================================================
