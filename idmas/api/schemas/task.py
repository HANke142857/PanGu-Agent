# =============================================================================
# 解析任务 Pydantic Schema
#
# 请求Schema:
#   - TaskCreateRequest: 创建任务请求
#     - drawing_id: UUID
#     - question: str (必填)
#     - background: str | None
#     - task_type: TaskType枚举
#     - prompt_mode: PromptMode枚举 (默认 standard_visual)
#
#   - TaskBatchRequest: 批量创建请求
#     - tasks: list[TaskCreateRequest]
#
#   - TaskReviewRequest: 审核提交请求
#     - reviews: list[LabelReview]
#       - label_id: str
#       - action: confirm | correct | reject
#       - corrected_name: str | None
#
# 响应Schema:
#   - TaskCreateResponse: 创建响应 (202)
#     - task_id: UUID
#     - status: str
#     - stream_url: str
#
#   - TaskDetailResponse: 任务详情
#     - id, status, drawing_id, question
#     - vision_result, ocr_result, design_result, process_result
#     - knowledge_result, report_result
#     - conflicts, human_decision
#     - inference_time_ms, total_tokens
#     - created_at, completed_at
#
#   - TaskListResponse: 任务列表 (分页)
#
#   - SSEEvent: SSE事件格式
#     - event: str (intent/vision/ocr/conflict/review/done/error)
#     - data: dict
# =============================================================================
