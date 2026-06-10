"""健康检查端点。"""
from __future__ import annotations
from fastapi import APIRouter
from idmas.api.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="基础健康检查")
async def health() -> HealthResponse:
    return HealthResponse(status="healthy", dependencies={})


@router.get("/health/live", response_model=HealthResponse, summary="存活检查 (K8s liveness)")
async def liveness() -> HealthResponse:
    return HealthResponse(status="healthy")


@router.get("/health/ready", response_model=HealthResponse, summary="就绪检查 (K8s readiness)")
async def readiness() -> HealthResponse:
    """MVP 阶段：只检查应用自身，不检查外部依赖。"""
    return HealthResponse(status="healthy", dependencies={"app": "ok"})
