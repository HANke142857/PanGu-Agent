"""全局错误处理：将领域异常统一映射为标准 JSON 响应。"""
from __future__ import annotations
import logging
import uuid
from fastapi import Request
from fastapi.responses import JSONResponse
from idmas.domain.shared.exceptions import IDMASError, RateLimitExceededError
from idmas.config.settings import get_settings

logger = logging.getLogger(__name__)


async def idmas_exception_handler(request: Request, exc: IDMASError) -> JSONResponse:
    settings = get_settings()
    request_id = str(uuid.uuid4())[:8]

    logger.error(
        "[%s] %s %s → %s: %s",
        request_id, request.method, request.url.path, exc.code, exc.message,
    )

    body: dict = {
        "error": {
            "code":       exc.code,
            "message":    exc.message,
            "request_id": request_id,
        }
    }

    # 开发环境附加 detail
    if settings.is_development and exc.detail:
        body["error"]["detail"] = exc.detail

    # 限流附加 retry_after
    if isinstance(exc, RateLimitExceededError):
        body["error"]["retry_after"] = exc.retry_after

    return JSONResponse(status_code=exc.http_status, content=body)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    settings   = get_settings()
    request_id = str(uuid.uuid4())[:8]
    logger.exception("[%s] Unhandled exception: %s", request_id, exc)

    body: dict = {
        "error": {
            "code":       "IDMAS-500-001",
            "message":    "Internal server error",
            "request_id": request_id,
        }
    }
    if settings.is_development:
        body["error"]["detail"] = str(exc)

    return JSONResponse(status_code=500, content=body)
