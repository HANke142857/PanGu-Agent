"""
PLM 回写路由。

POST /api/v1/plm/writeback   将已完成任务的解析结果回写目标 PLM（幂等）
POST /api/v1/plm/webhook     接收 PLM 推送的变更通知（HMAC 签名校验）

回写经 PLMWritebackService 组装载荷并调用品牌适配器；适配器基类保证幂等。
"""
from __future__ import annotations

from fastapi import APIRouter, Header, Request, Response

from idmas.api.schemas.plm import PLMWritebackRequest, PLMWritebackResponse
from idmas.services.plm_writeback import PLMWritebackService

router = APIRouter(prefix="/api/v1/plm", tags=["plm"])


@router.post("/writeback", response_model=PLMWritebackResponse, summary="回写解析结果到 PLM")
async def plm_writeback(body: PLMWritebackRequest, request: Request):
    service = PLMWritebackService(
        task_repo=request.app.state.task_repo,
        drawing_repo=request.app.state.drawing_repo,
        adapter_factory=request.app.state.plm_adapter_factory,
    )
    result = await service.writeback(body.task_id, body.target_system)
    return PLMWritebackResponse(**result.model_dump())


@router.post("/webhook", summary="接收 PLM 变更通知")
async def plm_webhook(
    request: Request,
    x_plm_system:    str = Header(default="teamcenter"),
    x_plm_signature: str = Header(default=""),
):
    payload = await request.body()
    adapter = request.app.state.plm_adapter_factory(x_plm_system)
    if not adapter.verify_webhook(x_plm_signature, payload):
        return Response(status_code=401)
    return {"received": True, "system": x_plm_system}
