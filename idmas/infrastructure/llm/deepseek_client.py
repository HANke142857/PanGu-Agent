"""
DeepSeek 文本推理客户端（OpenAI 兼容 API）。

用于主控 Agent 的**文本推理**（意图识别、对抗辩论裁决等）。DeepSeek 的 chat
模型是纯文本，不支持图像——视觉识别仍走视觉模型（vLLM / DeepSeek-VL）。

实现 BaseLLMClient.chat_completion；vision_inference 不支持（抛错）。
httpx 惰性导入。API Key 从 settings.DEEPSEEK_API_KEY（即环境变量）读取，不硬编码。

模型名经 settings.CHAT_MODEL 配置，默认 deepseek-v4-flash（DeepSeek V4，2026-04 发布；
另有 deepseek-v4-pro。遗留名 deepseek-chat/deepseek-reasoner 将于 2026-07-24 弃用）。
"""

from __future__ import annotations

import logging
import time
from typing import Any

from idmas.infrastructure.llm.vllm_client import BaseLLMClient, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"


class DeepSeekClient(BaseLLMClient):
    """OpenAI 兼容的 DeepSeek（或任意兼容端点）文本客户端。"""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout: int = 60,
        temperature: float = 0.3,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._temperature = temperature

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    async def chat_completion(
        self,
        messages: list[LLMMessage],
        max_tokens: int = 2048,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        import httpx  # 惰性导入

        if not self._api_key:
            raise RuntimeError("DEEPSEEK_API_KEY 未配置")

        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
            "temperature": self._temperature if temperature is None else temperature,
            "stream": False,
        }
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions", headers=self._headers(), json=payload
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            latency_ms=int((time.monotonic() - t0) * 1000),
            model=str(data.get("model", self._model)),
        )

    async def vision_inference(self, image_url: str, prompt: str, **kwargs: Any) -> LLMResponse:
        raise NotImplementedError(
            "DeepSeek chat 模型不支持图像推理；视觉识别请使用 vLLM/视觉模型"
        )

    async def health_check(self) -> bool:
        try:
            await self.chat_completion([LLMMessage(role="user", content="ping")], max_tokens=1)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("DeepSeek health_check 失败: %s", exc)
            return False


def build_chat_client(settings: Any) -> BaseLLMClient | None:
    """按 settings.CHAT_BACKEND 构造主控推理用文本客户端。

    返回 None 表示"不接 LLM"——主控的推理节点退化为规则式（默认行为）。
    """
    backend = getattr(settings, "CHAT_BACKEND", "fake")
    if backend in ("deepseek", "openai"):
        return DeepSeekClient(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            model=settings.CHAT_MODEL,
            temperature=settings.CHAT_TEMPERATURE,
        )
    return None
