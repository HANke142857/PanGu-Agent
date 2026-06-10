"""
vLLM 推理客户端。

BaseLLMClient  : 抽象接口（Protocol），供所有调用方依赖
VLLMClient     : 真实实现，调用 vLLM OpenAI-兼容 HTTP API（需 GPU）
FakeVLLMClient : 测试/开发用，无需 GPU，返回可配置的确定性响应

注入方式（依赖倒置）::

    # 测试 / 开发
    client: BaseLLMClient = FakeVLLMClient()

    # 生产
    client: BaseLLMClient = VLLMClient(settings)
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据契约
# ---------------------------------------------------------------------------

@dataclass
class LLMMessage:
    """单条消息。role: 'system' | 'user' | 'assistant'"""
    role:    str
    content: str | list[dict[str, Any]]   # 纯文本或含图片的多模态 content


@dataclass
class LLMResponse:
    """LLM 响应。"""
    content:       str
    prompt_tokens: int   = 0
    output_tokens: int   = 0
    latency_ms:    int   = 0
    model:         str   = ""
    cached:        bool  = False

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.output_tokens


# ---------------------------------------------------------------------------
# 抽象接口
# ---------------------------------------------------------------------------

class BaseLLMClient(ABC):
    """所有 LLM 客户端必须实现的接口。"""

    @abstractmethod
    async def chat_completion(
        self,
        messages:   list[LLMMessage],
        max_tokens: int   = 2048,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> LLMResponse:
        """纯文本对话补全。"""
        ...

    @abstractmethod
    async def vision_inference(
        self,
        image_url:  str,
        prompt:     str,
        max_tokens: int   = 2048,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> LLMResponse:
        """图片 + 文本的多模态推理。"""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """检查推理服务是否可用。"""
        ...


# ---------------------------------------------------------------------------
# VLLMClient（真实实现）
# ---------------------------------------------------------------------------

class VLLMClient(BaseLLMClient):
    """
    通过 vLLM 的 OpenAI-兼容 HTTP API 进行推理。
    内含熔断器（5 次连续失败 → 熔断）。
    需要 `pip install httpx`。
    """

    def __init__(self, settings: Any | None = None) -> None:
        # 懒导入，避免在未安装 httpx 时直接报错
        try:
            import httpx  # noqa: F401
        except ImportError as e:
            raise ImportError("VLLMClient requires `httpx`. Run: pip install httpx") from e

        from idmas.config.settings import get_settings
        cfg = settings or get_settings()

        self._url:            str   = cfg.VLLM_URL
        self._model:          str   = cfg.VLLM_MODEL
        self._max_tokens:     int   = cfg.VLLM_MAX_TOKENS
        self._temperature:    float = cfg.VLLM_TEMPERATURE
        self._timeout:        int   = cfg.VLLM_TIMEOUT
        self._max_concurrent: int   = cfg.VLLM_MAX_CONCURRENT

        from agents.shared.retry import CircuitBreaker
        self._circuit = CircuitBreaker(
            name="vllm",
            failure_threshold=5,
            recovery_timeout=60.0,
            success_threshold=3,
        )
        self._client: Any = None  # httpx.AsyncClient，懒初始化

    async def _get_client(self) -> Any:
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def chat_completion(
        self,
        messages:    list[LLMMessage],
        max_tokens:  int   = 2048,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> LLMResponse:
        payload = {
            "model":       self._model,
            "messages":    [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens":  max_tokens,
            "temperature": temperature,
        }
        return await self._post(payload)

    async def vision_inference(
        self,
        image_url:   str,
        prompt:      str,
        max_tokens:  int   = 2048,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> LLMResponse:
        """构造 OpenAI vision 格式的多模态请求。"""
        content = [
            {"type": "image_url", "image_url": {"url": image_url}},
            {"type": "text",      "text": prompt},
        ]
        payload = {
            "model":      self._model,
            "messages":   [{"role": "user", "content": content}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        return await self._post(payload)

    async def _post(self, payload: dict[str, Any]) -> LLMResponse:
        from idmas.domain.shared.exceptions import VLLMInferenceError

        if self._circuit.is_open():
            raise VLLMInferenceError("Circuit breaker OPEN — vLLM unavailable")

        client = await self._get_client()
        t0 = time.monotonic()
        try:
            resp = await client.post(
                f"{self._url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data    = resp.json()
            latency = int((time.monotonic() - t0) * 1000)
            choice  = data["choices"][0]["message"]["content"]
            usage   = data.get("usage", {})
            self._circuit.record_success()
            return LLMResponse(
                content=choice,
                prompt_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                latency_ms=latency,
                model=data.get("model", self._model),
            )
        except Exception as exc:
            self._circuit.record_failure()
            raise VLLMInferenceError(f"vLLM request failed: {exc}") from exc

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            resp   = await client.get(f"{self._url}/health")
            return resp.status_code == 200
        except Exception:
            return False


# ---------------------------------------------------------------------------
# FakeVLLMClient（开发 / 测试专用，零 GPU 依赖）
# ---------------------------------------------------------------------------

_DEFAULT_FAKE_LABELS = [
    {
        "label_id": "1",
        "name": "轴承座",
        "confidence": 0.92,
        "spatial_description": "图纸左上方传动轴区域",
        "bounding_box": {"x": 0.05, "y": 0.05, "width": 0.15, "height": 0.12},
    },
    {
        "label_id": "2",
        "name": "齿轮箱",
        "confidence": 0.88,
        "spatial_description": "图纸中央主体部分",
        "bounding_box": {"x": 0.35, "y": 0.30, "width": 0.30, "height": 0.35},
    },
    {
        "label_id": "3",
        "name": "输出轴",
        "confidence": 0.55,   # 故意低置信度，触发 OCR 重试路径
        "spatial_description": "图纸右侧输出端",
        "bounding_box": {"x": 0.75, "y": 0.40, "width": 0.18, "height": 0.10},
    },
]


class FakeVLLMClient(BaseLLMClient):
    """
    测试用假客户端。
    - 默认返回 _DEFAULT_FAKE_LABELS 中的标号 JSON
    - 可通过 custom_response 注入任意字符串响应
    - latency_ms 固定为 50ms，方便断言
    """

    def __init__(
        self,
        custom_response: str | None = None,
        fake_labels: list[dict[str, Any]] | None = None,
        raise_on_call: Exception | None = None,
    ) -> None:
        self._custom_response = custom_response
        self._fake_labels     = fake_labels or _DEFAULT_FAKE_LABELS
        self._raise_on_call   = raise_on_call
        self.call_count       = 0   # 便于测试断言

    def _build_response(self) -> str:
        if self._custom_response is not None:
            return self._custom_response
        return json.dumps({"labels": self._fake_labels}, ensure_ascii=False)

    async def chat_completion(
        self,
        messages:    list[LLMMessage],
        max_tokens:  int   = 2048,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> LLMResponse:
        self.call_count += 1
        if self._raise_on_call:
            raise self._raise_on_call
        return LLMResponse(
            content=self._build_response(),
            prompt_tokens=256,
            output_tokens=128,
            latency_ms=50,
            model="fake-vlm",
        )

    async def vision_inference(
        self,
        image_url:   str,
        prompt:      str,
        max_tokens:  int   = 2048,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> LLMResponse:
        self.call_count += 1
        if self._raise_on_call:
            raise self._raise_on_call
        logger.debug("[FakeVLLM] vision_inference called (url=%s, call=%d)", image_url, self.call_count)
        return LLMResponse(
            content=self._build_response(),
            prompt_tokens=512,
            output_tokens=256,
            latency_ms=50,
            model="fake-vlm",
        )

    async def health_check(self) -> bool:
        return True
