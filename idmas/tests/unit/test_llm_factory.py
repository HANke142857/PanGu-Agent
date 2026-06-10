"""
LLM 客户端工厂测试：按 LLM_BACKEND 选择 fake / vllm。
"""

from __future__ import annotations

from types import SimpleNamespace

from idmas.infrastructure.llm.vllm_client import (
    FakeVLLMClient,
    VLLMClient,
    build_llm_client,
)


def test_default_is_fake():
    client = build_llm_client(SimpleNamespace(LLM_BACKEND="fake"))
    assert isinstance(client, FakeVLLMClient)


def test_missing_attr_falls_back_to_fake():
    client = build_llm_client(SimpleNamespace())
    assert isinstance(client, FakeVLLMClient)


def test_vllm_backend_selects_real():
    settings = SimpleNamespace(
        LLM_BACKEND="vllm",
        VLLM_URL="http://localhost:8000",
        VLLM_MODEL="m",
        VLLM_MAX_TOKENS=2048,
        VLLM_TEMPERATURE=0.1,
        VLLM_TIMEOUT=60,
        VLLM_MAX_CONCURRENT=8,
    )
    client = build_llm_client(settings)
    assert isinstance(client, VLLMClient)
