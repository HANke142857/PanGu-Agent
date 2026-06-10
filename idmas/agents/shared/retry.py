"""
Agent 通用重试策略与熔断器。

RetryConfig  : 重试参数配置
with_retry   : 指数退避异步重试装饰器
CircuitBreaker: 熔断器（closed → open → half-open）
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# RetryConfig
# ---------------------------------------------------------------------------

@dataclass
class RetryConfig:
    """重试参数。"""
    max_retries:      int   = 3       # 最大重试次数（不含首次）
    base_delay:       float = 2.0     # 基础延迟秒数
    max_delay:        float = 30.0    # 最大延迟秒数
    exponential_base: float = 2.0     # 指数退避底数

    # 预设: vLLM 推理 — 2s, 4s, 8s
    VLLM: "RetryConfig" = field(default=None, init=False, repr=False)      # type: ignore[assignment]
    # 预设: PLM 回写 — 30s, 60s, 120s, 300s, 600s
    PLM:  "RetryConfig" = field(default=None, init=False, repr=False)      # type: ignore[assignment]

    def delay_for(self, attempt: int) -> float:
        """计算第 attempt 次重试的等待时长（0-indexed）。"""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


# 两种预设（模块级常量，避免循环引用）
RetryConfig.VLLM = RetryConfig(max_retries=3, base_delay=2.0, max_delay=8.0)   # type: ignore[misc]
RetryConfig.PLM  = RetryConfig(max_retries=5, base_delay=30.0, max_delay=600.0)  # type: ignore[misc]


# ---------------------------------------------------------------------------
# with_retry — 异步重试装饰器
# ---------------------------------------------------------------------------

def with_retry(
    config: RetryConfig | None = None,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """
    用法::

        @with_retry(RetryConfig.VLLM)
        async def call_vllm(...): ...
    """
    cfg = config or RetryConfig()

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(cfg.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < cfg.max_retries:
                        delay = cfg.delay_for(attempt)
                        logger.warning(
                            "[retry] %s failed (attempt %d/%d), retrying in %.1fs: %s",
                            func.__name__, attempt + 1, cfg.max_retries, delay, exc,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "[retry] %s exhausted %d retries: %s",
                            func.__name__, cfg.max_retries, exc,
                        )
            raise last_exc  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# CircuitBreaker
# ---------------------------------------------------------------------------

class CircuitState(str, Enum):
    CLOSED    = "closed"      # 正常，放行
    OPEN      = "open"        # 熔断，拒绝
    HALF_OPEN = "half_open"   # 探测，放行一次


class CircuitBreaker:
    """
    三态熔断器。

    - CLOSED  → OPEN    : 连续失败 failure_threshold 次
    - OPEN    → HALF_OPEN: 冷却时间 recovery_timeout 后
    - HALF_OPEN → CLOSED : 连续成功 success_threshold 次
    - HALF_OPEN → OPEN   : 任意失败
    """

    def __init__(
        self,
        name:              str   = "circuit",
        failure_threshold: int   = 5,
        recovery_timeout:  float = 60.0,  # 秒
        success_threshold: int   = 3,
    ) -> None:
        self.name               = name
        self.failure_threshold  = failure_threshold
        self.recovery_timeout   = recovery_timeout
        self.success_threshold  = success_threshold

        self._state:             CircuitState = CircuitState.CLOSED
        self._failure_count:     int          = 0
        self._success_count:     int          = 0
        self._last_failure_time: float        = 0.0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                logger.info("[circuit:%s] OPEN → HALF_OPEN", self.name)
                self._state         = CircuitState.HALF_OPEN
                self._success_count = 0
        return self._state

    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def record_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                logger.info("[circuit:%s] HALF_OPEN → CLOSED", self.name)
                self._state         = CircuitState.CLOSED
                self._failure_count = 0
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        self._failure_count    += 1
        self._last_failure_time = time.monotonic()
        if self._state == CircuitState.HALF_OPEN:
            logger.warning("[circuit:%s] HALF_OPEN → OPEN", self.name)
            self._state = CircuitState.OPEN
        elif self._failure_count >= self.failure_threshold:
            logger.warning(
                "[circuit:%s] CLOSED → OPEN (failures=%d)", self.name, self._failure_count,
            )
            self._state = CircuitState.OPEN

    def __call__(self, func: F) -> F:
        """作为装饰器使用。"""
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if self.is_open():
                from idmas.domain.shared.exceptions import VLLMInferenceError
                raise VLLMInferenceError(
                    f"Circuit breaker [{self.name}] is OPEN. Service unavailable."
                )
            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as exc:
                self.record_failure()
                raise exc

        return wrapper  # type: ignore[return-value]
