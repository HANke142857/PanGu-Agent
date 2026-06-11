"""前端日志回收端点：浏览器把运行时错误/警告回传，落盘 logs/frontend.log。"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/client-logs", tags=["logs"])

_fe_logger = logging.getLogger("idmas.frontend")


class ClientLogEntry(BaseModel):
    level:   str = "info"        # debug | info | warn | error
    message: str = ""
    url:     str | None = None
    stack:   str | None = None
    ts:      str | None = None


class ClientLogBatch(BaseModel):
    entries: list[ClientLogEntry] = Field(default_factory=list)


@router.post("", status_code=204, summary="接收前端浏览器日志")
async def ingest(batch: ClientLogBatch) -> Response:
    for e in batch.entries:
        lvl = getattr(logging, e.level.upper(), logging.INFO)
        suffix = f"\n{e.stack}" if e.stack else ""
        _fe_logger.log(lvl, "[%s] %s%s", e.url or "-", e.message, suffix)
    return Response(status_code=204)
