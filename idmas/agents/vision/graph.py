"""
Vision SubGraph 构建。

流程::

    preprocess_image
         ↓
    build_prompt
         ↓
    vllm_inference
         ↓
    parse_output
         ↓
    confidence_check
         ↓ (路由)
    needs_ocr_retry & retry_count < 1
         ├─ YES → ocr_retry → build_prompt → vllm_inference → ...
         └─ NO  → finalize → END

使用方法::

    from idmas.infrastructure.llm.vllm_client import FakeVLLMClient
    from idmas.agents.vision.graph import build_vision_graph

    graph  = await build_vision_graph(FakeVLLMClient())
    result = await graph.ainvoke({
        "image_url":   "http://minio/drawings/abc.png",
        "prompt_mode": "standard_visual",
    })
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from idmas.agents.vision.nodes import (
    build_prompt_node,
    confidence_check_node,
    finalize_node,
    make_ocr_retry_node,
    make_vllm_inference_node,
    parse_output_node,
    preprocess_image_node,
)
from idmas.agents.vision.state import VisionState
from idmas.infrastructure.llm.vllm_client import BaseLLMClient


# ---------------------------------------------------------------------------
# 条件路由
# ---------------------------------------------------------------------------

def _default_ocr_client():
    """按 settings.OCR_BACKEND 选择 OCR 客户端（paddle 真实 / fake 默认）。"""
    from idmas.config.settings import get_settings

    settings = get_settings()
    if settings.OCR_BACKEND == "paddle":
        from idmas.infrastructure.ocr.paddle_client import PaddleOCRClient
        return PaddleOCRClient(settings.OCR_URL, settings.OCR_TIMEOUT)

    from idmas.infrastructure.ocr.base import FakeOCRClient
    return FakeOCRClient()


def route_after_confidence(state: VisionState) -> str:
    """
    置信度检查后路由：
    - 有低置信度 且 未超重试次数 → ocr_retry
    - 否则 → finalize
    """
    if state.get("needs_ocr_retry") and (state.get("retry_count", 0) < 1):
        return "ocr_retry"
    return "finalize"


# ---------------------------------------------------------------------------
# 图构建工厂
# ---------------------------------------------------------------------------

async def build_vision_graph(
    llm_client: BaseLLMClient,
    ocr_client: Any | None = None,
):
    """
    构建并编译 Vision SubGraph。

    Args:
        llm_client: 实现 BaseLLMClient 的推理客户端（真实或 Fake）
        ocr_client: PaddleOCR 客户端（None 时使用 FakeOCR）

    Returns:
        编译后的 CompiledStateGraph，可直接 `.ainvoke()` / `.astream()`
    """
    # 1. 生成需要依赖注入的异步节点
    vllm_node      = await make_vllm_inference_node(llm_client)
    ocr_retry_node = await make_ocr_retry_node(ocr_client or _default_ocr_client())

    # 2. 构建 StateGraph
    builder = StateGraph(VisionState)

    # 注册所有节点
    builder.add_node("preprocess_image",  preprocess_image_node)
    builder.add_node("build_prompt",      build_prompt_node)
    builder.add_node("vllm_inference",    vllm_node)
    builder.add_node("parse_output",      parse_output_node)
    builder.add_node("confidence_check",  confidence_check_node)
    builder.add_node("ocr_retry",         ocr_retry_node)
    builder.add_node("finalize",          finalize_node)

    # 固定边
    builder.add_edge(START,              "preprocess_image")
    builder.add_edge("preprocess_image", "build_prompt")
    builder.add_edge("build_prompt",     "vllm_inference")
    builder.add_edge("vllm_inference",   "parse_output")
    builder.add_edge("parse_output",     "confidence_check")

    # 条件路由：confidence_check → ocr_retry 或 finalize
    builder.add_conditional_edges(
        "confidence_check",
        route_after_confidence,
        {
            "ocr_retry": "ocr_retry",
            "finalize":  "finalize",
        },
    )

    # OCR 重试后重走 build_prompt → vllm_inference
    builder.add_edge("ocr_retry",  "build_prompt")
    builder.add_edge("finalize",   END)

    # 3. 编译
    return builder.compile()
