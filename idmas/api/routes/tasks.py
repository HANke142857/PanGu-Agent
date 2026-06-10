"""
解析任务路由。

POST /api/v1/tasks             创建并同步执行解析任务
GET  /api/v1/tasks/{id}        查询任务结果
GET  /api/v1/tasks             任务列表（分页）
POST /api/v1/tasks/{id}/review 提交人工审核结果
"""
from __future__ import annotations
import time
import uuid
from uuid import UUID

from fastapi import APIRouter, Query, Request

from idmas.api.schemas.task import (
    TaskCreateRequest, TaskCreateResponse, TaskDetailResponse,
    TaskListResponse, TaskReviewRequest,
)
from idmas.domain.analysis.entities import AnalysisTask, ReviewRecord
from idmas.domain.analysis.value_objects import (
    PromptMode, ReviewAction, TaskStatus, TaskType,
)
from idmas.domain.drawing.entities import DrawingLabel, LabelSource
from idmas.domain.drawing.value_objects import BoundingBox, SpatialInfo
from idmas.domain.shared.exceptions import DrawingNotFoundError, TaskNotFoundError
from idmas.domain.shared.value_objects import Confidence

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def _repos(request: Request):
    return request.app.state.drawing_repo, request.app.state.task_repo


def _llm(request: Request):
    return request.app.state.llm_client


# ── POST /api/v1/tasks ─────────────────────────────────────────────────────

@router.post("", status_code=202, response_model=TaskCreateResponse, summary="创建解析任务")
async def create_task(body: TaskCreateRequest, request: Request):
    drawing_repo, task_repo = _repos(request)
    llm_client              = _llm(request)

    # 校验图纸存在
    drawing = await drawing_repo.get_by_id(body.drawing_id)
    if not drawing:
        raise DrawingNotFoundError(str(body.drawing_id))

    # 创建任务实体
    task_id = uuid.uuid4()
    thread_id = f"thread-{task_id}"
    task = AnalysisTask(
        id          = task_id,
        drawing_id  = body.drawing_id,
        user_id     = uuid.UUID("00000000-0000-0000-0000-000000000001"),  # MVP: 固定用户
        task_type   = body.task_type,
        prompt_mode = body.prompt_mode,
        question    = body.question,
        background  = body.background,
    )
    await task_repo.save(task)
    task.mark_processing(thread_id)

    # 运行 Master Graph（含 Vision + 可选 Design/Process/Knowledge + Report）
    t0 = time.monotonic()
    try:
        from idmas.agents.master.graph import build_master_graph
        graph, _ = await build_master_graph(
            llm_client           = llm_client,
            enable_human_review  = True,
        )
        thread_id = f"thread-{task_id}"
        config    = {"configurable": {"thread_id": thread_id}}
        result    = await graph.ainvoke(
            {
                "image_url":   drawing.file_url,
                "prompt_mode": body.prompt_mode.value,
                "task_type":   body.task_type.value,
                "user_query":  body.question,
                "request_id":  str(task_id),
                "messages":    [],
            },
            config=config,
        )

        elapsed_ms   = int((time.monotonic() - t0) * 1000)
        total_tokens = 0

        # Master graph 结果字段
        vision_final = result.get("vision_result") or {}
        task.vision_result  = vision_final
        task.design_result  = result.get("design_result") or {}
        task.process_result = result.get("process_result") or {}
        task.knowledge_result = result.get("knowledge_result") or {}
        task.report_result  = result.get("report_result") or {}

        if vision_final.get("success") or vision_final.get("labels"):
            # 保存识别出的标号
            raw_labels  = vision_final.get("labels", [])
            new_labels  = []
            for raw in raw_labels:
                bb_data = raw.get("bounding_box", {})
                try:
                    bbox    = BoundingBox(**bb_data)
                    spatial = SpatialInfo.from_bounding_box(bbox, raw.get("spatial_description", ""))
                except Exception:
                    bbox    = BoundingBox(x=0.0, y=0.0, width=0.1, height=0.1)
                    spatial = SpatialInfo.from_bounding_box(bbox)

                new_labels.append(DrawingLabel(
                    drawing_id   = body.drawing_id,
                    label_id     = str(raw.get("label_id", "")),
                    name         = str(raw.get("name", "")),
                    confidence   = Confidence(value=float(raw.get("confidence", 0.0))),
                    bounding_box = bbox,
                    spatial_info = spatial,
                    source       = LabelSource.VISION_AGENT,
                ))
            await drawing_repo.save_labels(new_labels)

            # 判断是否需要人工审核
            needs_review = any(raw.get("needs_review") for raw in raw_labels)
            if needs_review:
                task.mark_waiting_review()
            else:
                task.mark_completed(elapsed_ms, total_tokens)
        else:
            master_status = result.get("status", "")
            if master_status == "waiting_review":
                task.mark_waiting_review()
            elif master_status == "failed":
                task.mark_failed("IDMAS-502-002", result.get("error") or "Master Agent failed")
            else:
                task.mark_failed("IDMAS-502-002", "Vision Agent returned no labels")

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        task.mark_failed("IDMAS-502-002", str(exc))

    await task_repo.save(task)

    return TaskCreateResponse(
        task_id    = task.id,
        status     = task.status,
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
