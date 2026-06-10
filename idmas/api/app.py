"""
FastAPI 应用工厂。
create_app() 负责组装所有路由、中间件、生命周期事件。
通过 app.state 共享依赖（LLM 客户端、仓储），便于测试替换。
"""
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from idmas.api.middleware.error_handler import idmas_exception_handler, generic_exception_handler
from idmas.api.routes import health, drawings, tasks, plm
from idmas.config.settings import get_settings
from idmas.domain.shared.exceptions import IDMASError
from idmas.infrastructure.db.memory_repositories import (
    InMemoryDrawingRepository,
    InMemoryAnalysisTaskRepository,
)
from idmas.infrastructure.llm.vllm_client import BaseLLMClient, build_llm_client


def _build_task_queue(settings, drawing_repo, task_repo, llm_client, metrics=None):
    """按配置组装任务队列。

    - rabbitmq：仅发布，结果由独立 Worker 进程异步回写
    - eager（默认）：发布即就地处理，保持单机/测试的同步语义
    """
    if settings.MQ_BACKEND == "rabbitmq":
        from idmas.infrastructure.mq.publisher import RabbitMQTaskQueue
        return RabbitMQTaskQueue(settings.RABBITMQ_URL)

    from idmas.infrastructure.mq.base import EagerTaskQueue
    from idmas.services.task_processor import TaskProcessor

    processor = TaskProcessor(drawing_repo, task_repo, llm_client, metrics=metrics)
    return EagerTaskQueue(handler=processor.handle)


def _build_storage(settings):
    """按配置组装对象存储客户端。"""
    if settings.STORAGE_BACKEND == "minio":
        from idmas.infrastructure.storage.minio_client import MinioStorageClient
        return MinioStorageClient(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            bucket=settings.MINIO_BUCKET,
            secure=settings.MINIO_SECURE,
        )
    from idmas.infrastructure.storage.base import InMemoryStorageClient
    return InMemoryStorageClient(bucket=settings.MINIO_BUCKET)


def _build_plm_factory(settings):
    """按配置组装 PLM 适配器工厂：system 名称 -> 适配器实例。"""
    if settings.PLM_BACKEND == "real":
        from idmas.infrastructure.adapters.enovia import EnoviaAdapter
        from idmas.infrastructure.adapters.inteplm import IntePLMAdapter
        from idmas.infrastructure.adapters.teamcenter import TeamcenterAdapter

        builders = {
            "teamcenter": lambda: TeamcenterAdapter(
                settings.PLM_TEAMCENTER_URL, settings.PLM_AUTH_TOKEN, settings.PLM_WEBHOOK_SECRET),
            "enovia": lambda: EnoviaAdapter(
                settings.PLM_ENOVIA_URL, settings.PLM_AUTH_TOKEN, settings.PLM_WEBHOOK_SECRET),
            "inteplm": lambda: IntePLMAdapter(
                settings.PLM_INTEPLM_URL, settings.PLM_AUTH_TOKEN, settings.PLM_WEBHOOK_SECRET),
        }
        cache: dict = {}

        def factory(system: str):
            key = system.lower()
            if key not in builders:
                raise ValueError(f"未知 PLM 系统: {system}")
            return cache.setdefault(key, builders[key]())

        return factory

    # fake：所有 system 共用一个实例（幂等与回写记录跨调用保留）
    from idmas.infrastructure.adapters.base import FakePLMAdapter
    shared = FakePLMAdapter(webhook_secret=settings.PLM_WEBHOOK_SECRET)
    return lambda system: shared


def _build_cache(settings):
    """按配置组装缓存客户端。"""
    if settings.CACHE_BACKEND == "redis":
        from idmas.infrastructure.cache.redis_client import RedisCacheClient
        return RedisCacheClient(settings.REDIS_URL)
    from idmas.infrastructure.cache.base import InMemoryCacheClient
    return InMemoryCacheClient()


def create_app(
    llm_client:   BaseLLMClient | None = None,
    drawing_repo=None,
    task_repo=None,
    task_queue=None,
    storage=None,
    plm_factory=None,
    cache=None,
) -> FastAPI:
    """
    创建 FastAPI 实例。

    Args:
        llm_client:   注入 LLM 客户端（None → 自动根据环境选择）
        drawing_repo: 注入图纸仓储（None → 内存仓储）
        task_repo:    注入任务仓储（None → 内存仓储）
        task_queue:   注入任务队列（None → 按 MQ_BACKEND 选择 eager/rabbitmq）
        storage:      注入对象存储（None → 按 STORAGE_BACKEND 选择 memory/minio）
    """
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # ── 启动 ────────────────────────────────────────────────────────
        app.state.llm_client = llm_client or build_llm_client(settings)

        use_sql = settings.DB_BACKEND == "sql"
        if use_sql and (drawing_repo is None or task_repo is None):
            # 仅在选用 SQL 后端时才触碰数据库依赖，开发环境无需 PostgreSQL。
            from idmas.infrastructure.db.repositories import (
                SQLAnalysisTaskRepository,
                SQLDrawingRepository,
            )
            from idmas.infrastructure.db.session import get_session_factory, init_db

            await init_db()
            factory = get_session_factory()
            app.state.drawing_repo = drawing_repo or SQLDrawingRepository(factory)
            app.state.task_repo    = task_repo    or SQLAnalysisTaskRepository(factory)
        else:
            app.state.drawing_repo = drawing_repo or InMemoryDrawingRepository()
            app.state.task_repo    = task_repo    or InMemoryAnalysisTaskRepository()

        # ── 指标 ──────────────────────────────────────────────────────────
        from idmas.infrastructure.observability.metrics import build_metrics
        app.state.metrics = build_metrics(settings)

        # ── 缓存 ──────────────────────────────────────────────────────────
        app.state.cache = cache or _build_cache(settings)

        # ── 对象存储 ──────────────────────────────────────────────────────
        app.state.storage = storage or _build_storage(settings)
        await app.state.storage.ensure_bucket()

        # ── PLM 适配器工厂 ────────────────────────────────────────────────
        app.state.plm_adapter_factory = plm_factory or _build_plm_factory(settings)

        # ── 任务队列 ──────────────────────────────────────────────────────
        app.state.task_queue = task_queue or _build_task_queue(
            settings, app.state.drawing_repo, app.state.task_repo,
            app.state.llm_client, app.state.metrics,
        )

        yield

        # ── 关闭（清理资源）────────────────────────────────────────────
        await app.state.task_queue.close()
        await app.state.cache.close()
        if use_sql:
            from idmas.infrastructure.db.session import close_db
            await close_db()

    app = FastAPI(
        title       = "IDMAS — 工业图纸智能解析系统",
        version     = "0.1.0",
        description = "Industrial Drawing Multi-Agent System API",
        docs_url    = "/docs",
        redoc_url   = "/redoc",
        lifespan    = lifespan,
    )

    # ── CORS ────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins     = settings.APP_CORS_ORIGINS,
        allow_credentials = True,
        allow_methods     = ["*"],
        allow_headers     = ["*"],
    )

    # ── 限流（opt-in，基于 app.state.cache 计数）────────────────────────
    if settings.RATE_LIMIT_ENABLED:
        from idmas.api.middleware.rate_limit import RateLimitMiddleware
        app.add_middleware(RateLimitMiddleware, per_minute=settings.RATE_LIMIT_PER_MINUTE)

    # ── 分布式追踪（OTel，默认关闭）──────────────────────────────────────
    from idmas.infrastructure.observability.tracing import init_tracing, instrument_fastapi
    init_tracing(settings, "idmas-api")
    instrument_fastapi(app, settings)

    # ── 指标中间件 + /metrics 端点 ──────────────────────────────────────
    from idmas.api.middleware.metrics import MetricsMiddleware
    app.add_middleware(MetricsMiddleware)

    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint():
        from starlette.responses import Response
        body, content_type = app.state.metrics.render()
        return Response(content=body, media_type=content_type)

    # ── 异常处理 ─────────────────────────────────────────────────────────
    app.add_exception_handler(IDMASError, idmas_exception_handler)          # type: ignore
    app.add_exception_handler(Exception,  generic_exception_handler)        # type: ignore

    # ── 路由 ─────────────────────────────────────────────────────────────
    app.include_router(health.router,   prefix="/api/v1")
    app.include_router(drawings.router)
    app.include_router(tasks.router)
    app.include_router(plm.router)

    return app
