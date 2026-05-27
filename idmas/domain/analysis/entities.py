# =============================================================================
# 解析任务领域实体
#
# 包含:
#   - AnalysisTask: 解析任务实体(聚合根)
#     - id: UUID
#     - drawing_id: 关联图纸ID
#     - user_id: 创建用户ID
#     - task_type: 任务类型 (label_recognition/design_analysis/process_check等)
#     - prompt_mode: Prompt模式 (standard_visual/cot_visual等)
#     - question: 用户提问
#     - background: 背景信息
#     - status: 任务状态 (created/processing/waiting_review/completed/failed)
#     - langgraph_thread_id: LangGraph线程ID (用于状态恢复)
#     - vision_result / ocr_result / design_result / process_result
#     - knowledge_result / report_result: 各Agent输出
#     - conflicts: 冲突信息列表
#     - human_decision: 人工审核决策
#     - inference_time_ms: 推理耗时
#     - total_tokens: 消耗Token数
#     - model_version: 使用的模型版本
#     - error_code / error_message: 错误信息
#
#   - ReviewRecord: 审核记录实体
#     - id: UUID
#     - task_id: 关联任务ID
#     - reviewer_id: 审核人ID
#     - label_id: 审核标号
#     - original_name: 原识别名称
#     - corrected_name: 修正名称
#     - action: 审核动作 (confirm/correct/reject)
#     - feedback_status: 反馈状态 (pending/approved/rejected)
# =============================================================================
