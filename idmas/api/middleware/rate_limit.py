"""
API 限流中间件（固定窗口，基于缓存计数）。

每分钟按 客户端IP + 路径 计数：incr_with_ttl(key, 60)。超过阈值返回
429 + Retry-After + 错误码 IDMAS-429-001。缓存为 InMemory 时单机生效，
Redis 时多实例共享。

opt-in：settings.RATE_LIMIT_ENABLED=True 时由 create_app 挂载。
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, per_minute: int, prefixes: tuple[str, ...] = ("/api/v1/",)) -> None:
        super().__init__(app)
        self._per_minute = per_minute
        self._prefixes = prefixes

    def _limited_path(self, path: str) -> bool:
        return path.startswith(self._prefixes)

    async def dispatch(self, request: Request, call_next):
        cache = getattr(request.app.state, "cache", None)
        path = request.url.path
        if cache is None or not self._limited_path(path):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client}:{path}"
        try:
            count = await cache.incr_with_ttl(key, ttl=60)
        except Exception:  # noqa: BLE001 — 限流是旁路，故障不应拦截请求
            return await call_next(request)

        if count > self._per_minute:
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": "60"},
                content={"error": {
                    "code": "IDMAS-429-001",
                    "message": "请求过于频繁，请稍后重试",
                    "retry_after": 60,
                }},
            )
        return await call_next(request)
