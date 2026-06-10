"""
分布式链路追踪（OpenTelemetry → OTLP/Jaeger）。

跨 api → RabbitMQ → worker → vLLM/Milvus/PG 的全链路追踪，定位慢在哪一跳。

默认关闭（TRACING_ENABLED=False）→ 全部 no-op，零开销、零依赖。
最佳努力：OTel 包缺失或初始化失败时静默降级，不阻断启动。

用法::
    init_tracing(settings, "idmas-api")          # 进程启动时一次
    instrument_fastapi(app, settings)            # API 自动埋点
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_initialized = False


def init_tracing(settings: Any, service_name: str) -> bool:
    """初始化 TracerProvider + OTLP 导出。返回是否成功启用。"""
    global _initialized
    if _initialized or not getattr(settings, "TRACING_ENABLED", False):
        return _initialized
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _initialized = True
        logger.info("OTel tracing 已启用 service=%s", service_name)
    except Exception as exc:  # noqa: BLE001 — 追踪是旁路，缺包/失败则降级
        logger.warning("OTel tracing 不可用（%s），跳过分布式追踪", exc)
    return _initialized


def instrument_fastapi(app: Any, settings: Any) -> None:
    """对 FastAPI + httpx + sqlalchemy 自动埋点（启用时）。"""
    if not getattr(settings, "TRACING_ENABLED", False):
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
    except Exception as exc:  # noqa: BLE001
        logger.warning("FastAPI OTel 埋点失败（%s）", exc)
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        HTTPXClientInstrumentor().instrument()
    except Exception:  # noqa: BLE001 — httpx 埋点可选
        pass


def reset_for_tests() -> None:
    """测试辅助：复位初始化标志。"""
    global _initialized
    _initialized = False
