# =============================================================================
# 解析任务仓储接口 (Analysis Task Repository Interface)
#
# 接口方法:
#   - get_by_id(task_id: UUID) -> AnalysisTask | None
#   - save(task: AnalysisTask) -> AnalysisTask
#   - update_status(task_id: UUID, status: TaskStatus) -> None
#   - update_result(task_id: UUID, field: str, result: dict) -> None
#   - list_by_user(user_id: UUID, status: str|None, offset, limit) -> list
#   - list_pending_reviews() -> list[AnalysisTask]
#   - save_review(review: ReviewRecord) -> ReviewRecord
#   - get_reviews_by_task(task_id: UUID) -> list[ReviewRecord]
# =============================================================================
