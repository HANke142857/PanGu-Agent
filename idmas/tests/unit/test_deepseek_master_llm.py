"""
DeepSeek 文本客户端 + 主控 LLM 驱动（意图/辩论）测试。
真实 HTTP 调用用 Fake httpx 替身，不联网。
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from idmas.agents.master.nodes import _extract_json, make_debate_node, make_intent_node
from idmas.infrastructure.llm.deepseek_client import DeepSeekClient, build_chat_client
from idmas.infrastructure.llm.vllm_client import FakeVLLMClient, LLMMessage


# ── Fake httpx ──────────────────────────────────────────────────────────

class _Resp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class _FakeClient:
    captured = {}

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, headers=None, json=None):
        _FakeClient.captured = {"url": url, "headers": headers, "json": json}
        return _Resp({
            "choices": [{"message": {"content": '{"winner": "vision"}'}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 4},
            "model": "deepseek-v4-flash",
        })


class TestBuildChatClient:
    def test_fake_returns_none(self):
        assert build_chat_client(SimpleNamespace(CHAT_BACKEND="fake")) is None

    def test_deepseek_returns_client(self):
        c = build_chat_client(SimpleNamespace(
            CHAT_BACKEND="deepseek", DEEPSEEK_API_KEY="sk-x",
            DEEPSEEK_BASE_URL="https://api.deepseek.com", CHAT_MODEL="deepseek-v4-flash",
            CHAT_TEMPERATURE=0.3))
        assert isinstance(c, DeepSeekClient)


class TestDeepSeekClient:
    async def test_chat_completion(self, monkeypatch):
        import httpx
        monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)
        c = DeepSeekClient(api_key="sk-test", model="deepseek-v4-flash")
        resp = await c.chat_completion([LLMMessage(role="user", content="hi")])
        assert resp.content == '{"winner": "vision"}'
        assert resp.prompt_tokens == 12 and resp.output_tokens == 4
        # 请求带上了 Bearer key 与正确 endpoint
        assert _FakeClient.captured["headers"]["Authorization"] == "Bearer sk-test"
        assert _FakeClient.captured["url"].endswith("/chat/completions")

    async def test_missing_key_raises(self):
        with pytest.raises(RuntimeError):
            await DeepSeekClient(api_key="").chat_completion([LLMMessage(role="user", content="x")])

    async def test_vision_not_supported(self):
        with pytest.raises(NotImplementedError):
            await DeepSeekClient(api_key="k").vision_inference("url", "p")


class TestExtractJson:
    def test_plain(self):
        assert _extract_json('{"a": 1}') == {"a": 1}

    def test_fenced(self):
        assert _extract_json('```json\n{"a": 2}\n```')["a"] == 2

    def test_garbage(self):
        assert _extract_json("no json here") == {}


class TestIntentNodeLLM:
    async def test_llm_classifies_knowledge_query(self):
        client = FakeVLLMClient(custom_response='{"intent": "knowledge_query"}')
        node = make_intent_node(client)
        out = await node({"user_query": "轴承座是什么", "image_url": "x", "task_type": "label_recognition"})
        assert out["intent"] == "knowledge_only"
        assert out["required_agents"] == ["vision", "knowledge"]
        assert out["task_type"] == "knowledge_query"

    async def test_none_uses_rules(self):
        node = make_intent_node(None)
        out = await node({"task_type": "comprehensive"})
        assert out["required_agents"] == ["vision", "design", "process", "knowledge"]

    async def test_bad_json_falls_back_to_rules(self):
        client = FakeVLLMClient(custom_response="这不是JSON")
        node = make_intent_node(client)
        out = await node({"task_type": "design_analysis"})
        assert out["required_agents"] == ["vision", "design"]   # 规则结果


class TestDebateNodeLLM:
    def _state_with_unresolved_conflict(self):
        # gap 0.05 < 0.15 → 规则无法自动裁决
        return {"conflicts": [{
            "label_id": "1", "vision_name": "轴承座", "knowledge_name": "端盖",
            "vision_confidence": 0.80, "knowledge_confidence": 0.75, "resolution": None,
        }]}

    async def test_llm_resolves_unresolved(self):
        client = FakeVLLMClient(custom_response='{"winner": "vision"}')
        node = make_debate_node(client)
        out = await node(self._state_with_unresolved_conflict())
        assert out["debate_resolved"] is True
        assert out["conflicts"][0]["resolution"] == "轴承座"
        assert out["conflicts"][0]["resolved_by"] == "llm"

    async def test_none_rule_only_leaves_unresolved(self):
        node = make_debate_node(None)
        out = await node(self._state_with_unresolved_conflict())
        assert out["debate_resolved"] is False
