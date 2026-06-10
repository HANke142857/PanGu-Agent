"""
请求指标中间件：对每个请求记录延迟与计数（按方法 + 路由模板 + 状态码）。

用路由模板（如 /api/v1/tasks/{task_id}）而非原始路径，避免 UUID 撑爆指标基数。
依赖 app.state.metrics（默认 NoopMetrics，零开销）。
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        metrics = getattr(request.app.state, "metrics", None)
        if metrics is None:
            return await call_next(request)

        t0 = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - t0

        route = request.scope.get("route")
        path = getattr(route, "path", None) or request.url.path
        try:
            metrics.observe_request(request.method, path, response.status_code, duration)
        except Exception:  # noqa: BLE001 — 指标失败不影响请求
            pass
        return response
