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
from idmas.api.routes import health, drawings, tasks
from idmas.config.settings import get_settings
from idmas.domain.shared.exceptions import IDMASError
from idmas.infrastructure.db.memory_repositories import (
    InMemoryDrawingRepository,
    InMemoryAnalysisTaskRepository,
)
from idmas.infrastructure.llm.vllm_client import BaseLLMClient, FakeVLLMClient


def _build_task_queue(settings, drawing_repo, task_repo, llm_client):
    """按配置组装任务队列。

    - rabbitmq：仅发布，结果由独立 Worker 进程异步回写
    - eager（默认）：发布即就地处理，保持单机/测试的同步语义
    """
    if settings.MQ_BACKEND == "rabbitmq":
        from idmas.infrastructure.mq.publisher import RabbitMQTaskQueue
        return RabbitMQTaskQueue(settings.RABBITMQ_URL)

    from idmas.infrastructure.mq.base import EagerTaskQueue
    from idmas.services.task_processor import TaskProcessor

    processor = TaskProcessor(drawing_repo, task_repo, llm_client)
    return EagerTaskQueue(handler=processor.handle)


def create_app(
    llm_client:   BaseLLMClient | None = None,
    drawing_repo=None,
    task_repo=None,
    task_queue=None,
) -> FastAPI:
    """
    创建 FastAPI 实例。

    Args:
        llm_client:   注入 LLM 客户端（None → 自动根据环境选择）
        drawing_repo: 注入图纸仓储（None → 内存仓储）
        task_repo:    注入任务仓储（None → 内存仓储）
        task_queue:   注入任务队列（None → 按 MQ_BACKEND 选择 eager/rabbitmq）
    """
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # ── 启动 ────────────────────────────────────────────────────────
        app.state.llm_client = llm_client or FakeVLLMClient()

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

        # ── 任务队列 ──────────────────────────────────────────────────────
        app.state.task_queue = task_queue or _build_task_queue(
            settings, app.state.drawing_repo, app.state.task_repo, app.state.llm_client
        )

        yield

        # ── 关闭（清理资源）────────────────────────────────────────────
        await app.state.task_queue.close()
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

    # ── 异常处理 ─────────────────────────────────────────────────────────
    app.add_exception_handler(IDMASError, idmas_exception_handler)          # type: ignore
    app.add_exception_handler(Exception,  generic_exception_handler)        # type: ignore

    # ── 路由 ─────────────────────────────────────────────────────────────
    app.include_router(health.router,   prefix="/api/v1")
    app.include_router(drawings.router)
    app.include_router(tasks.router)

    return app
