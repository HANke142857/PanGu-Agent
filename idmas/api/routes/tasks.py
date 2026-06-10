"""
解析任务路由。

POST /api/v1/tasks             创建解析任务并入队（异步处理，202 Accepted）
GET  /api/v1/tasks/{id}        查询任务结果
GET  /api/v1/tasks             任务列表（分页）
POST /api/v1/tasks/{id}/review 提交人工审核结果

处理流程：路由只负责落库 + 发布 task.created 消息，真正的 Master Graph 执行
由 services.TaskProcessor 承担（eager 队列就地执行 / rabbitmq 队列交 Worker）。
"""
from __future__ import annotations
import uuid
from uuid import UUID

from fastapi import APIRouter, Query, Request

from idmas.api.schemas.task import (
    TaskCreateRequest, TaskCreateResponse, TaskDetailResponse,
    TaskListResponse, TaskReviewRequest,
)
from idmas.domain.analysis.entities import AnalysisTask, ReviewRecord
from idmas.domain.analysis.value_objects import ReviewAction, TaskStatus
from idmas.domain.shared.exceptions import DrawingNotFoundError, TaskNotFoundError
from idmas.infrastructure.mq.base import TaskMessage

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def _repos(request: Request):
    return request.app.state.drawing_repo, request.app.state.task_repo


def _queue(request: Request):
    return request.app.state.task_queue


# ── POST /api/v1/tasks ─────────────────────────────────────────────────────

@router.post("", status_code=202, response_model=TaskCreateResponse, summary="创建解析任务")
async def create_task(body: TaskCreateRequest, request: Request):
    drawing_repo, task_repo = _repos(request)
    task_queue              = _queue(request)

    # 校验图纸存在
    drawing = await drawing_repo.get_by_id(body.drawing_id)
    if not drawing:
        raise DrawingNotFoundError(str(body.drawing_id))

    # 创建任务实体（created 状态落库）
    task = AnalysisTask(
        id          = uuid.uuid4(),
        drawing_id  = body.drawing_id,
        user_id     = uuid.UUID("00000000-0000-0000-0000-000000000001"),  # MVP: 固定用户
        task_type   = body.task_type,
        prompt_mode = body.prompt_mode,
        question    = body.question,
        background  = body.background,
    )
    await task_repo.save(task)

    # 入队：eager 队列就地处理完毕后任务已是终态；rabbitmq 队列则仍为 created。
    await task_queue.publish(TaskMessage(task_id=task.id, drawing_id=body.drawing_id))

    # 重新读取以反映处理后的最新状态（eager 场景）
    latest = await task_repo.get_by_id(task.id)
    status = latest.status if latest else task.status

    return TaskCreateResponse(
        task_id    = task.id,
        status     = status,
        stream_url = f"/api/v1/tasks/{task.id}/stream",
    )


# ── GET /api/v1/tasks/{id} ─────────────────────────────────────────────────

@router.get("/{task_id}", response_model=TaskDetailResponse, summary="查询任务结果")
async def get_task(task_id: UUID, request: Request):
    _, task_repo = _repos(request)
    task = await task_repo.get_by_id(task_id)
    if not task:
        raise TaskNotFoundError(str(task_id))
    return _to_response(task)


# ── GET /api/v1/tasks ──────────────────────────────────────────────────────

@router.get("", response_model=TaskListResponse, summary="任务列表")
async def list_tasks(
    request: Request,
    offset:  int = Query(default=0, ge=0),
    limit:   int = Query(default=20, ge=1, le=100),
):
    _, task_repo = _repos(request)
    all_tasks = list(task_repo._tasks.values())
    page      = all_tasks[offset: offset + limit]
    return TaskListResponse(
        items=[_to_response(t) for t in page],
        total=task_repo.count,
        offset=offset,
        limit=limit,
    )


# ── POST /api/v1/tasks/{id}/review ────────────────────────────────────────

@router.post("/{task_id}/review", status_code=200, summary="提交人工审核结果")
async def submit_review(task_id: UUID, body: TaskReviewRequest, request: Request):
    drawing_repo, task_repo = _repos(request)
    task = await task_repo.get_by_id(task_id)
    if not task:
        raise TaskNotFoundError(str(task_id))

    reviewer_id = uuid.UUID("00000000-0000-0000-0000-000000000002")  # MVP: 固定审核人
    for rev in body.reviews:
        try:
            action = ReviewAction(rev.action)
        except ValueError:
            action = ReviewAction.confirm

        record = ReviewRecord(
            task_id        = task_id,
            reviewer_id    = reviewer_id,
            label_id       = rev.label_id,
            original_name  = "",
            corrected_name = rev.corrected_name,
            action         = action,
        )
        await task_repo.save_review(record)

        # 如果是修正动作，同步更新标号
        if action == ReviewAction.correct and rev.corrected_name:
            labels = await drawing_repo.get_labels(task.drawing_id)
            for lbl in labels:
                if lbl.label_id == rev.label_id:
                    lbl.correct(rev.corrected_name)
            await drawing_repo.save_labels(labels)

    # 审核完成后将任务标记为 completed
    if task.status == TaskStatus.waiting_review:
        task.mark_completed(
            inference_time_ms=task.inference_time_ms or 0,
            total_tokens=task.total_tokens,
        )
        await task_repo.save(task)

    return {"message": "审核已提交", "task_id": str(task_id)}


# ── 辅助 ──────────────────────────────────────────────────────────────────

def _to_response(task: AnalysisTask) -> TaskDetailResponse:
    return TaskDetailResponse(
        id                = task.id,
        status            = task.status,
        drawing_id        = task.drawing_id,
        task_type         = task.task_type,
        prompt_mode       = task.prompt_mode,
        question          = task.question,
        vision_result     = task.vision_result,
        conflicts         = [c.model_dump() for c in task.conflicts],
        human_decision    = task.human_decision,
        inference_time_ms = task.inference_time_ms,
        total_tokens      = task.total_tokens,
        error_code        = task.error_code,
        error_message     = task.error_message,
        created_at        = task.created_at,
        updated_at        = task.updated_at,
    )
