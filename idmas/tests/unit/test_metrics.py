"""
指标采集单元测试。
"""

from __future__ import annotations

from types import SimpleNamespace

from idmas.infrastructure.observability.metrics import (
    NoopMetrics,
    PrometheusMetrics,
    build_metrics,
    start_metrics_server,
)


class TestNoopMetrics:
    def test_all_noops(self):
        m = NoopMetrics()
        m.observe_request("GET", "/x", 200, 0.1)
        m.observe_agent("master", 0.2)
        m.inc_task("completed")
        m.inc_tokens(100)
        m.inc_conflict()
        m.set_queue_size(5)
        body, ctype = m.render()
        assert body == b"" and "text/plain" in ctype

    def test_start_server_noop_safe(self):
        # NoopMetrics 不应尝试绑定端口
        start_metrics_server(NoopMetrics(), 9999)


class TestPrometheusMetrics:
    def test_records_and_renders(self):
        m = PrometheusMetrics()
        m.observe_request("POST", "/api/v1/tasks", 202, 0.05)
        m.inc_task("waiting_review")
        m.inc_tokens(256)
        m.inc_conflict(2)
        m.set_queue_size(7)
        body, ctype = m.render()
        text = body.decode()
        assert "idmas_request_total" in text
        assert 'path="/api/v1/tasks"' in text
        assert "idmas_task_total" in text
        assert "idmas_tokens_total" in text
        assert "text/plain" in ctype

    def test_independent_registries(self):
        # 两个实例各自独立 registry，不冲突（多次 create_app 场景）
        m1, m2 = PrometheusMetrics(), PrometheusMetrics()
        m1.inc_task("completed")
        assert "idmas_task_total" in m2.render()[0].decode()


class TestBuildMetrics:
    def test_disabled_returns_noop(self):
        assert isinstance(build_metrics(SimpleNamespace(METRICS_ENABLED=False)), NoopMetrics)

    def test_enabled_returns_prometheus(self):
        assert isinstance(build_metrics(SimpleNamespace(METRICS_ENABLED=True)), PrometheusMetrics)

    def test_missing_attr_defaults_noop(self):
        assert isinstance(build_metrics(SimpleNamespace()), NoopMetrics)
