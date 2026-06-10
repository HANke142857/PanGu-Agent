"""
Prometheus 指标采集。

与项目其它基础设施一致（抽象接口 + No-op + 真实实现 + 开关）::

    BaseMetrics       : 抽象接口，业务只依赖它
    NoopMetrics       : 默认，全部空操作（测试/未启用时零开销）
    PrometheusMetrics : 真实实现（需 prometheus_client）

黄金指标（API 延迟/请求数/错误）+ 业务指标（任务状态、token、冲突、队列积压）。
每个 PrometheusMetrics 实例持有独立 CollectorRegistry，避免多次 create_app
导致的指标重复注册。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

CONTENT_TYPE_PLAIN = "text/plain; charset=utf-8"


class BaseMetrics(ABC):
    @abstractmethod
    def observe_request(self, method: str, path: str, status: int, duration_s: float) -> None: ...

    @abstractmethod
    def observe_agent(self, agent: str, duration_s: float) -> None: ...

    @abstractmethod
    def inc_task(self, status: str) -> None: ...

    @abstractmethod
    def inc_tokens(self, n: int) -> None: ...

    @abstractmethod
    def inc_conflict(self, n: int = 1) -> None: ...

    @abstractmethod
    def set_queue_size(self, n: int) -> None: ...

    @abstractmethod
    def render(self) -> tuple[bytes, str]:
        """返回 (exposition_bytes, content_type)，供 /metrics 端点输出。"""
        ...


class NoopMetrics(BaseMetrics):
    def observe_request(self, method, path, status, duration_s): ...
    def observe_agent(self, agent, duration_s): ...
    def inc_task(self, status): ...
    def inc_tokens(self, n): ...
    def inc_conflict(self, n=1): ...
    def set_queue_size(self, n): ...

    def render(self) -> tuple[bytes, str]:
        return b"", CONTENT_TYPE_PLAIN


class PrometheusMetrics(BaseMetrics):
    def __init__(self) -> None:
        from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

        self._registry = CollectorRegistry()
        self.request_total = Counter(
            "idmas_request_total", "API 请求总数",
            ["method", "path", "status"], registry=self._registry)
        self.request_duration = Histogram(
            "idmas_request_duration_seconds", "API 请求延迟",
            ["method", "path"], registry=self._registry)
        self.agent_duration = Histogram(
            "idmas_agent_duration_seconds", "Agent 执行耗时",
            ["agent"], registry=self._registry)
        self.task_total = Counter(
            "idmas_task_total", "任务状态计数", ["status"], registry=self._registry)
        self.tokens_total = Counter(
            "idmas_tokens_total", "Token 消耗总量", registry=self._registry)
        self.conflict_total = Counter(
            "idmas_conflict_total", "冲突触发次数", registry=self._registry)
        self.queue_size = Gauge(
            "idmas_task_queue_size", "任务队列积压数", registry=self._registry)

    def observe_request(self, method, path, status, duration_s):
        self.request_total.labels(method, path, str(status)).inc()
        self.request_duration.labels(method, path).observe(duration_s)

    def observe_agent(self, agent, duration_s):
        self.agent_duration.labels(agent).observe(duration_s)

    def inc_task(self, status):
        self.task_total.labels(status).inc()

    def inc_tokens(self, n):
        if n:
            self.tokens_total.inc(n)

    def inc_conflict(self, n=1):
        self.conflict_total.inc(n)

    def set_queue_size(self, n):
        self.queue_size.set(n)

    @property
    def registry(self):
        return self._registry

    def render(self) -> tuple[bytes, str]:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        return generate_latest(self._registry), CONTENT_TYPE_LATEST


def start_metrics_server(metrics: BaseMetrics, port: int) -> None:
    """为无 HTTP 端口的进程（Worker）暴露 /metrics。NoopMetrics 时空操作。"""
    if not isinstance(metrics, PrometheusMetrics):
        return
    from prometheus_client import start_http_server

    start_http_server(port, registry=metrics.registry)


def build_metrics(settings) -> BaseMetrics:
    """按 settings.METRICS_ENABLED 选择真实 / No-op 指标。"""
    if getattr(settings, "METRICS_ENABLED", False):
        try:
            return PrometheusMetrics()
        except Exception:  # noqa: BLE001 — prometheus_client 缺失则降级
            return NoopMetrics()
    return NoopMetrics()
