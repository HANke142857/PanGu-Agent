"""
LangFuse + OTel 可观测性（默认关闭 / 优雅降级）单元测试。
"""

from __future__ import annotations

from types import SimpleNamespace

from idmas.infrastructure.observability.langfuse_handler import build_langfuse_callbacks
from idmas.infrastructure.observability import tracing


class TestLangfuse:
    def test_disabled_returns_empty(self):
        assert build_langfuse_callbacks(SimpleNamespace(LANGFUSE_ENABLED=False)) == []

    def test_missing_attr_returns_empty(self):
        assert build_langfuse_callbacks(SimpleNamespace()) == []

    def test_enabled_graceful(self):
        # 启用但包可能缺失 → 返回 list（0 或 1 个回调），绝不抛异常
        s = SimpleNamespace(
            LANGFUSE_ENABLED=True,
            LANGFUSE_PUBLIC_KEY="pk", LANGFUSE_SECRET_KEY="sk",
            LANGFUSE_HOST="http://localhost:3000",
        )
        out = build_langfuse_callbacks(s, trace_name="t", session_id="s1")
        assert isinstance(out, list)
        assert len(out) in (0, 1)


class TestTracing:
    def setup_method(self):
        tracing.reset_for_tests()

    def teardown_method(self):
        tracing.reset_for_tests()

    def test_disabled_noop(self):
        assert tracing.init_tracing(SimpleNamespace(TRACING_ENABLED=False), "idmas-api") is False

    def test_missing_attr_noop(self):
        assert tracing.init_tracing(SimpleNamespace(), "svc") is False

    def test_enabled_graceful(self):
        # 启用但包可能缺失 → 返回 bool，不抛异常
        s = SimpleNamespace(
            TRACING_ENABLED=True,
            OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317",
        )
        result = tracing.init_tracing(s, "idmas-api")
        assert isinstance(result, bool)

    def test_instrument_fastapi_disabled_noop(self):
        # 关闭时不应触碰 app
        tracing.instrument_fastapi(object(), SimpleNamespace(TRACING_ENABLED=False))
