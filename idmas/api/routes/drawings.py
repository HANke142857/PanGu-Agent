"""
图纸管理路由。

POST /api/v1/drawings      上传图纸（multipart），立即触发 Vision 解析，同步返回结果
GET  /api/v1/drawings/{id} 获取图纸详情（含已识别标号）
GET  /api/v1/drawings      图纸列表（分页 + 关键词搜索）
"""
from __future__ import annotations
import time
import uuid
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, File, Query

from idmas.api.schemas.drawing import (
    DrawingCreateRequest, DrawingListResponse, DrawingResponse, LabelResponse,
)
from idmas.domain.drawing.entities import Drawing, DrawingLabel, LabelSource
from idmas.domain.drawing.value_objects import (
    BoundingBox, DrawingType, FileFormat, LifecycleState, SpatialInfo,
)
from idmas.domain.shared.exceptions import (
    DrawingNotFoundError, InvalidDrawingError, StorageError,
)
from idmas.domain.shared.value_objects import Confidence

router = APIRouter(prefix="/api/v1/drawings", tags=["drawings"])

# ── 允许的文件格式 ──────────────────────────────────────────────────────────
_ALLOWED_EXTENSIONS = {fmt.value for fmt in FileFormat}
_MAX_FILE_SIZE      = 50 * 1024 * 1024   # 50 MB


def _get_repos(request: Request):
    return request.app.state.drawing_repo, request.app.state.task_repo


def _get_llm_client(request: Request):
    return request.app.state.llm_client


# ── POST /api/v1/drawings ──────────────────────────────────────────────────

@router.post("", status_code=201, response_model=DrawingResponse, summary="上传图纸并解析")
async def upload_drawing(
    request:      Request,
    file:         UploadFile = File(..., description="图纸文件 (png/jpg/pdf/dwg/dxf)"),
    title:        str        = Form(...),
    drawing_type: str        = Form(default="assembly"),
    prompt_mode:  str        = Form(default="standard_visual"),
    source_system: str       = Form(default=""),
    source_doc_id: str       = Form(default=""),
):
    drawing_repo, _ = _get_repos(request)
    llm_client      = _get_llm_client(request)

    # 1. 格式校验
    suffix = (file.filename or "").rsplit(".", 1)[-1].lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise InvalidDrawingError(
            f"不支持的文件格式 '.{suffix}'，允许: {_ALLOWED_EXTENSIONS}"
        )

    # 2. 读取文件并上传对象存储
    file_bytes = await file.read()
    if len(file_bytes) > _MAX_FILE_SIZE:
        raise InvalidDrawingError(
            f"文件超过 50MB 限制: {len(file_bytes) / 1024 / 1024:.1f}MB"
        )

    storage      = request.app.state.storage
    drawing_id   = uuid.uuid4()
    object_name  = f"{drawing_id}/{file.filename}"
    try:
        file_url = await storage.upload(file_bytes, object_name)
        sha256   = storage.compute_sha256(file_bytes)
    except Exception as exc:
        # 对象存储不可用（如 MinIO 未启动）——转成清晰的 502，而非裸 500
        import logging
        logging.getLogger(__name__).error("对象存储上传失败: %s", exc, exc_info=True)
        raise StorageError(
            message="对象存储不可用，图纸上传失败",
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc

    # 3. 构造 Drawing 实体
    try:
        dtype = DrawingType(drawing_type)
    except ValueError:
        dtype = DrawingType.assembly

    try:
        fmt = FileFormat(suffix)
    except ValueError:
        fmt = FileFormat.png

    drawing = Drawing(
        id              = drawing_id,
        title           = title,
        drawing_type    = dtype,
        file_format     = fmt,
        file_url        = file_url,
        file_size_bytes = len(file_bytes),
        source_system   = source_system,
        source_doc_id   = source_doc_id,
        lifecycle_state = LifecycleState.draft,
        metadata        = {"object_name": object_name, "sha256": sha256},
    )
    await drawing_repo.save(drawing)

    # 4. 触发 Vision Agent 解析（同步）
    labels: list[DrawingLabel] = []
    t0 = time.monotonic()
    try:
        from idmas.agents.vision.graph import build_vision_graph
        graph  = await build_vision_graph(llm_client)
        result = await graph.ainvoke({
            "image_url":   file_url,
            "prompt_mode": prompt_mode,
            "drawing_id":  str(drawing_id),
        })

        final = result.get("final_result") or {}
        if final.get("success") and final.get("labels"):
            for raw in final["labels"]:
                bb_data = raw.get("bounding_box", {})
                try:
                    bbox    = BoundingBox(**bb_data)
                    spatial = SpatialInfo.from_bounding_box(bbox, raw.get("spatial_description", ""))
                except Exception:
                    bbox    = BoundingBox(x=0.0, y=0.0, width=0.1, height=0.1)
                    spatial = SpatialInfo.from_bounding_box(bbox)

                labels.append(DrawingLabel(
                    drawing_id   = drawing_id,
                    label_id     = str(raw.get("label_id", "")),
                    name         = str(raw.get("name", "")),
                    confidence   = Confidence(value=float(raw.get("confidence", 0.0))),
                    bounding_box = bbox,
                    spatial_info = spatial,
                    source       = LabelSource.VISION_AGENT,
                ))
            await drawing_repo.save_labels(labels)
    except Exception as exc:
        # 解析失败不影响图纸入库，记录但不抛出
        import logging
        logging.getLogger(__name__).warning("Vision Agent failed for drawing %s: %s", drawing_id, exc)

    elapsed_ms = int((time.monotonic() - t0) * 1000)

    return _to_response(drawing, labels)


# ── GET /api/v1/drawings/{id} ──────────────────────────────────────────────

@router.get("/{drawing_id}", response_model=DrawingResponse, summary="获取图纸详情")
async def get_drawing(drawing_id: UUID, request: Request):
    drawing_repo, _ = _get_repos(request)
    drawing = await drawing_repo.get_by_id(drawing_id)
    if not drawing:
        raise DrawingNotFoundError(str(drawing_id))
    labels = await drawing_repo.get_labels(drawing_id)
    return _to_response(drawing, labels)


# ── GET /api/v1/drawings/{id}/file ─────────────────────────────────────────

@router.get("/{drawing_id}/file", summary="下载图纸原始文件")
async def download_drawing_file(drawing_id: UUID, request: Request):
    drawing_repo, _ = _get_repos(request)
    storage         = request.app.state.storage
    drawing = await drawing_repo.get_by_id(drawing_id)
    if not drawing:
        raise DrawingNotFoundError(str(drawing_id))

    object_name = (drawing.metadata or {}).get("object_name")
    if not object_name:
        raise DrawingNotFoundError(f"{drawing_id} (无关联文件)")

    from idmas.infrastructure.storage.base import ObjectNotFoundError, guess_content_type
    try:
        data = await storage.download(object_name)
    except ObjectNotFoundError:
        raise DrawingNotFoundError(f"{drawing_id} (文件已删除)")

    from fastapi import Response
    return Response(content=data, media_type=guess_content_type(object_name))


# ── GET /api/v1/drawings ───────────────────────────────────────────────────

@router.get("", response_model=DrawingListResponse, summary="图纸列表")
async def list_drawings(
    request: Request,
    keyword: str = Query(default="", description="标题关键词搜索"),
    offset:  int = Query(default=0, ge=0),
    limit:   int = Query(default=20, ge=1, le=100),
):
    drawing_repo, _ = _get_repos(request)
    if keyword:
        drawings = await drawing_repo.search_by_title(keyword, limit=limit)
        total    = len(drawings)
    else:
        drawings = await drawing_repo.list_all(offset=offset, limit=limit)
        total    = await drawing_repo.count_all()

    items = []
    for d in drawings:
        labels = await drawing_repo.get_labels(d.id)
        items.append(_to_response(d, labels))

    return DrawingListResponse(
        items=items, total=total, offset=offset, limit=limit,
    )


# ── 辅助 ──────────────────────────────────────────────────────────────────

def _to_response(drawing: Drawing, labels: list[DrawingLabel]) -> DrawingResponse:
    label_resp = [
        LabelResponse(
            label_id            = lbl.label_id,
            name                = lbl.name,
            confidence          = lbl.confidence.value,
            needs_review        = lbl.needs_review,
            spatial_description = lbl.spatial_info.region if lbl.spatial_info else None,
            quadrant            = lbl.spatial_info.quadrant.value if lbl.spatial_info else None,
            bounding_box        = {
                "x": lbl.bounding_box.x, "y": lbl.bounding_box.y,
                "width": lbl.bounding_box.width, "height": lbl.bounding_box.height,
            },
        )
        for lbl in labels
    ]
    return DrawingResponse(
        id              = drawing.id,
        title           = drawing.title,
        drawing_type    = drawing.drawing_type,
        file_format     = drawing.file_format,
        file_url        = drawing.file_url,
        file_size_bytes = drawing.file_size_bytes,
        lifecycle_state = drawing.lifecycle_state,
        source_system   = drawing.source_system,
        labels          = label_resp,
        label_count     = len(label_resp),
        created_at      = drawing.created_at,
        updated_at      = drawing.updated_at,
    )
