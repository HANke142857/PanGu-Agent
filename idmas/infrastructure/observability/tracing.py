# =============================================================================
# 分布式链路追踪 (OpenTelemetry + Jaeger)
#
# 职责:
#   - 初始化OTel TracerProvider
#   - 自动注入trace_id/span_id到日志
#   - HTTP请求自动追踪 (FastAPI instrumentor)
#   - 自定义Span创建 (Agent节点级追踪)
#
# 配置:
#   - OTEL_EXPORTER_OTLP_ENDPOINT: Jaeger地址
#   - OTEL_SERVICE_NAME: idmas-api / idmas-worker
#
# 方法:
#   - init_tracing(service_name: str) -> None
#   - get_tracer() -> Tracer
#   - create_span(name, attributes) -> Span
# =============================================================================
