"""
Agent 层单元测试。
覆盖：FakeVLLMClient、Vision 节点函数、Vision Graph 端到端、
      重试装饰器、熔断器状态机。
全部纯内存，无 GPU / DB / 网络依赖。
"""

from __future__ import annotations

import asyncio
import json

import pytest

# ---------------------------------------------------------------------------
# FakeVLLMClient
# ---------------------------------------------------------------------------

from idmas.infrastructure.llm.vllm_client import (
    FakeVLLMClient,
    LLMMessage,
    LLMResponse,
)
from idmas.domain.shared.exceptions import VLLMInferenceError


class TestFakeVLLMClient:
    @pytest.mark.asyncio
    async def test_health_check(self):
        client = FakeVLLMClient()
        assert await client.health_check() is True

    @pytest.mark.asyncio
    async def test_vision_inference_returns_json(self):
        client = FakeVLLMClient()
        resp   = await client.vision_inference(
            image_url="http://fake/drawing.png",
            prompt="识别标号",
        )
        assert isinstance(resp, LLMResponse)
        data = json.loads(resp.content)
        assert "labels" in data
        assert len(data["labels"]) > 0

    @pytest.mark.asyncio
    async def test_chat_completion(self):
        client = FakeVLLMClient(custom_response='{"answer": "ok"}')
        resp   = await client.chat_completion(
            messages=[LLMMessage(role="user", content="test")]
        )
        assert resp.content == '{"answer": "ok"}'

    @pytest.mark.asyncio
    async def test_call_count(self):
        client = FakeVLLMClient()
        await client.vision_inference("url1", "p1")
        await client.vision_inference("url2", "p2")
        assert client.call_count == 2

    @pytest.mark.asyncio
    async def test_raise_on_call(self):
        client = FakeVLLMClient(raise_on_call=VLLMInferenceError("GPU OOM"))
        with pytest.raises(VLLMInferenceError):
            await client.vision_inference("url", "prompt")

    @pytest.mark.asyncio
    async def test_custom_labels(self):
        custom = [{"label_id": "X", "name": "自定义", "confidence": 0.99,
                   "spatial_description": "中央", "bounding_box": {"x": 0.4, "y": 0.4, "width": 0.2, "height": 0.2}}]
        client = FakeVLLMClient(fake_labels=custom)
        resp   = await client.vision_inference("url", "p")
        data   = json.loads(resp.content)
        assert data["labels"][0]["label_id"] == "X"


# ---------------------------------------------------------------------------
# Vision 节点单元测试（不启动完整 LangGraph）
# ---------------------------------------------------------------------------

from idmas.agents.vision.nodes import (
    build_prompt_node,
    confidence_check_node,
    finalize_node,
    parse_output_node,
    preprocess_image_node,
)
from idmas.agents.vision.state import VisionState


class TestPreprocessImageNode:
    def test_valid_url(self):
        state: VisionState = {"image_url": "http://minio/a.png", "prompt_mode": "standard_visual"}
        result = preprocess_image_node(state)
        assert result["needs_ocr_retry"] is False
        assert result["retry_count"] == 0
        assert result["error_message"] is None

    def test_empty_url(self):
        state: VisionState = {"image_url": ""}
        result = preprocess_image_node(state)
        assert "error_message" in result
        assert result["error_message"] is not None


class TestBuildPromptNode:
    def test_standard_mode(self):
        state: VisionState = {"prompt_mode": "standard_visual", "retry_count": 0}
        result = build_prompt_node(state)
        assert "current_prompt" in result
        assert "JSON" in result["current_prompt"]

    def test_cot_mode(self):
        state: VisionState = {"prompt_mode": "cot_visual", "retry_count": 0}
        result = build_prompt_node(state)
        assert "cot_steps" in result["current_prompt"] or "步骤" in result["current_prompt"]

    def test_ocr_augmented_on_retry(self):
        state: VisionState = {
            "prompt_mode": "standard_visual",
            "retry_count": 1,
            "ocr_results": [{"text": "3", "score": 0.95, "box": [0.75, 0.40]}],
        }
        result = build_prompt_node(state)
        assert "OCR" in result["current_prompt"]

    def test_unknown_mode_falls_back_to_standard(self):
        state: VisionState = {"prompt_mode": "nonexistent_mode", "retry_count": 0}
        result = build_prompt_node(state)
        assert result["current_prompt"]   # 不为空


class TestParseOutputNode:
    def _make_valid_json(self) -> str:
        return json.dumps({
            "labels": [
                {"label_id": "1", "name": "轴承座", "confidence": 0.92,
                 "spatial_description": "左上",
                 "bounding_box": {"x": 0.05, "y": 0.05, "width": 0.15, "height": 0.12}},
            ]
        }, ensure_ascii=False)

    def test_valid_json(self):
        state: VisionState = {"raw_llm_output": self._make_valid_json()}
        result = parse_output_node(state)
        assert result["parsed_labels"] is not None
        assert len(result["parsed_labels"]) == 1
        assert result["parsed_labels"][0]["name"] == "轴承座"

    def test_json_in_code_block(self):
        raw = f'```json\n{self._make_valid_json()}\n```'
        state: VisionState = {"raw_llm_output": raw}
        result = parse_output_node(state)
        assert result["parsed_labels"] is not None

    def test_invalid_json(self):
        state: VisionState = {"raw_llm_output": "这不是JSON内容"}
        result = parse_output_node(state)
        assert result["parsed_labels"] is None
        assert "error_message" in result

    def test_empty_output(self):
        state: VisionState = {"raw_llm_output": ""}
        result = parse_output_node(state)
        assert result["parsed_labels"] is None

    def test_skips_if_error_upstream(self):
        state: VisionState = {
            "raw_llm_output": self._make_valid_json(),
            "error_message": "upstream error",
        }
        result = parse_output_node(state)
        assert result.get("parsed_labels") is None

    def test_invalid_bbox_filtered(self):
        raw = json.dumps({"labels": [
            {"label_id": "1", "name": "好", "confidence": 0.9,
             "spatial_description": "中",
             "bounding_box": {"x": 0.0, "y": 0.0, "width": 0.5, "height": 0.5}},
            {"label_id": "2", "name": "坏", "confidence": 0.8,
             "spatial_description": "右",
             "bounding_box": {"x": 0.9, "y": 0.9, "width": 0.5, "height": 0.5}},  # 溢出
        ]})
        state: VisionState = {"raw_llm_output": raw}
        result = parse_output_node(state)
        # 溢出的 bbox 被过滤，只留 1 个
        assert len(result["parsed_labels"]) == 1


class TestConfidenceCheckNode:
    def _labels(self, confidences: list[float]) -> list[dict]:
        return [
            {"label_id": str(i + 1), "name": f"part{i}", "confidence": c,
             "spatial_description": "", "bounding_box": {"x": 0.0, "y": 0.0, "width": 0.1, "height": 0.1}}
            for i, c in enumerate(confidences)
        ]

    def test_all_high(self):
        state: VisionState = {
            "parsed_labels": self._labels([0.92, 0.88, 0.85]),
            "retry_count": 0,
        }
        result = confidence_check_node(state)
        assert result["needs_ocr_retry"] is False
        assert len(result["confidence_scores"]) == 3

    def test_has_low_confidence(self):
        state: VisionState = {
            "parsed_labels": self._labels([0.92, 0.55]),  # 第2个低
            "retry_count": 0,
        }
        result = confidence_check_node(state)
        assert result["needs_ocr_retry"] is True

    def test_no_retry_after_max(self):
        """已达最大重试次数时，不再触发 OCR 重试。"""
        state: VisionState = {
            "parsed_labels": self._labels([0.92, 0.40]),
            "retry_count": 1,   # 已经重试过了
        }
        result = confidence_check_node(state)
        assert result["needs_ocr_retry"] is False

    def test_empty_labels(self):
        state: VisionState = {"parsed_labels": [], "retry_count": 0}
        result = confidence_check_node(state)
        assert result["needs_ocr_retry"] is False


class TestFinalizeNode:
    def test_success(self):
        labels = [
            {"label_id": "1", "name": "轴承座", "confidence": 0.92,
             "spatial_description": "左上", "bounding_box": {"x": 0.05, "y": 0.05, "width": 0.15, "height": 0.12}},
        ]
        state: VisionState = {
            "parsed_labels":    labels,
            "confidence_scores": {"1": 0.92},
            "retry_count":      0,
            "cot_steps":        [],
        }
        result = finalize_node(state)
        assert result["final_result"]["success"] is True
        assert result["final_result"]["label_count"] == 1

    def test_needs_review_flag(self):
        labels = [
            {"label_id": "1", "name": "未知", "confidence": 0.45,
             "spatial_description": "右", "bounding_box": {"x": 0.7, "y": 0.1, "width": 0.1, "height": 0.1}},
        ]
        state: VisionState = {
            "parsed_labels":    labels,
            "confidence_scores": {"1": 0.45},
            "retry_count":      0,
            "cot_steps":        [],
        }
        result = finalize_node(state)
        assert result["final_result"]["labels"][0]["needs_review"] is True

    def test_error_propagates(self):
        state: VisionState = {
            "parsed_labels": None,
            "error_message": "GPU OOM",
        }
        result = finalize_node(state)
        assert result["final_result"]["success"] is False
        assert "GPU OOM" in result["final_result"]["error"]


# ---------------------------------------------------------------------------
# Vision Graph 端到端（用 FakeVLLMClient）
# ---------------------------------------------------------------------------

from idmas.agents.vision.graph import build_vision_graph


class TestVisionGraph:
    @pytest.mark.asyncio
    async def test_full_flow_standard(self):
        """标准 Prompt 模式全流程，FakeVLLM 含低置信度标号 → 触发 OCR 重试。"""
        client = FakeVLLMClient()
        graph  = await build_vision_graph(client)

        result = await graph.ainvoke({
            "image_url":   "http://minio/test/gear_box.png",
            "prompt_mode": "standard_visual",
        })

        assert result["final_result"] is not None
        assert result["final_result"]["success"] is True
        # 默认 FakeVLLM 含 3 个标号（含 1 个低置信度 → OCR 重试 → 再次推理）
        assert result["final_result"]["label_count"] == 3
        # OCR 重试触发了 1 次
        assert result["retry_count"] == 1
        # LLM 被调用了 2 次（首次 + OCR 重试后 1 次）
        assert client.call_count == 2

    @pytest.mark.asyncio
    async def test_full_flow_all_high_confidence(self):
        """所有标号高置信度时，不触发 OCR 重试。"""
        high_conf_labels = [
            {"label_id": "1", "name": "轴承座", "confidence": 0.95,
             "spatial_description": "左上", "bounding_box": {"x": 0.05, "y": 0.05, "width": 0.15, "height": 0.12}},
            {"label_id": "2", "name": "齿轮箱", "confidence": 0.90,
             "spatial_description": "中央", "bounding_box": {"x": 0.35, "y": 0.30, "width": 0.30, "height": 0.35}},
        ]
        client = FakeVLLMClient(fake_labels=high_conf_labels)
        graph  = await build_vision_graph(client)

        result = await graph.ainvoke({
            "image_url":   "http://minio/test/drawing.png",
            "prompt_mode": "standard_visual",
        })

        assert result["final_result"]["success"] is True
        assert result.get("retry_count", 0) == 0   # 未触发重试
        assert client.call_count == 1               # 只调用 1 次

    @pytest.mark.asyncio
    async def test_empty_image_url(self):
        """空 URL 场景：preprocess 节点拦截，final_result 反映错误。"""
        client = FakeVLLMClient()
        graph  = await build_vision_graph(client)

        result = await graph.ainvoke({"image_url": "", "prompt_mode": "standard_visual"})
        # 出错后 finalize 应输出 success=False
        assert result["final_result"]["success"] is False
        assert client.call_count == 0   # LLM 未被调用

    @pytest.mark.asyncio
    async def test_vllm_failure(self):
        """LLM 调用失败：最终输出 success=False，不崩溃。"""
        client = FakeVLLMClient(raise_on_call=VLLMInferenceError("服务不可用"))
        graph  = await build_vision_graph(client)

        result = await graph.ainvoke({
            "image_url":   "http://minio/test/drawing.png",
            "prompt_mode": "standard_visual",
        })
        assert result["final_result"]["success"] is False

    @pytest.mark.asyncio
    async def test_cot_mode(self):
        """CoT 模式流程能正常结束。"""
        client = FakeVLLMClient()
        graph  = await build_vision_graph(client)

        result = await graph.ainvoke({
            "image_url":   "http://minio/test/patent.png",
            "prompt_mode": "cot_visual",
        })
        assert result["final_result"]["success"] is True


# ---------------------------------------------------------------------------
# 重试装饰器
# ---------------------------------------------------------------------------

from idmas.agents.shared.retry import RetryConfig, with_retry


class TestRetry:
    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        calls = []

        @with_retry(RetryConfig(max_retries=3, base_delay=0.01))
        async def task():
            calls.append(1)
            return "ok"

        result = await task()
        assert result == "ok"
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_success_after_retry(self):
        calls = []

        @with_retry(RetryConfig(max_retries=3, base_delay=0.01))
        async def task():
            calls.append(1)
            if len(calls) < 3:
                raise ValueError("not yet")
            return "ok"

        result = await task()
        assert result == "ok"
        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_exhausted_retries(self):
        @with_retry(RetryConfig(max_retries=2, base_delay=0.01))
        async def task():
            raise ValueError("always fail")

        with pytest.raises(ValueError):
            await task()

    def test_delay_for(self):
        cfg = RetryConfig(max_retries=3, base_delay=2.0, max_delay=30.0, exponential_base=2.0)
        assert cfg.delay_for(0) == pytest.approx(2.0)
        assert cfg.delay_for(1) == pytest.approx(4.0)
        assert cfg.delay_for(2) == pytest.approx(8.0)
        # max_delay 上限
        assert cfg.delay_for(10) == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# 熔断器
# ---------------------------------------------------------------------------

from idmas.agents.shared.retry import CircuitBreaker, CircuitState


class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_open_after_failures(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_not_open_before_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_after_recovery_timeout(self):
        import time
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.02)   # 等待冷却
        assert cb.state == CircuitState.HALF_OPEN

    def test_closed_after_success_in_half_open(self):
        import time
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01, success_threshold=2)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.02)
        _ = cb.state   # 触发 OPEN → HALF_OPEN
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_reopen_on_failure_in_half_open(self):
        import time
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.02)
        _ = cb.state   # 触发 HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_is_open(self):
        cb = CircuitBreaker(failure_threshold=1)
        assert not cb.is_open()
        cb.record_failure()
        assert cb.is_open()
