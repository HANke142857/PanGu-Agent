# =============================================================================
# Agent重试策略
#
# 包含:
#   - RetryConfig: 重试配置
#     - max_retries: 最大重试次数
#     - base_delay: 基础延迟(秒)
#     - max_delay: 最大延迟(秒)
#     - exponential_base: 指数退避基数
#
#   - with_retry: 重试装饰器
#     支持指数退避: delay = base_delay * (exponential_base ^ attempt)
#     PLM回写重试: 30s, 60s, 120s, 300s, 600s (共5次)
#     vLLM推理重试: 2s, 4s, 8s (共3次)
#
#   - CircuitBreaker: 熔断器
#     状态: closed → open → half-open
#     vLLM: 5次连续>30s → 熔断, 3次连续成功 → 恢复
# =============================================================================
