"""
Vision SubGraph 节点函数。

每个节点：
  - 接收 VisionState
  - 返回 dict（仅含要更新的字段）
  - 不抛异常——错误写入 error_message，由路由决定如何处理

LLM 客户端通过工厂函数注入，不在模块层硬编码（便于测试替换 Fake）。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from idmas.agents.vision.state import VisionState
from idmas.config.prompts.vision_prompts import PROMPT_MAP, build_ocr_augmented_prompt
from idmas.domain.drawing.value_objects import BoundingBox, ImageDimension, SpatialInfo
from idmas.domain.shared.value_objects import Confidence
from idmas.infrastructure.llm.vllm_client import BaseLLMClient

logger = logging.getLogger(__name__)

# OCR 重试最大次数
MAX_OCR_RETRIES = 1
# 触发 OCR 重试的置信度阈值
LOW_CONFIDENCE_THRESHOLD = 0.60


# ---------------------------------------------------------------------------
# 节点 1: preprocess_image_node
# ---------------------------------------------------------------------------

def preprocess_image_node(state: VisionState) -> dict[str, Any]:
    """
    图片预处理：校验 URL、尺寸（若可知）。
    MVP 阶段不做实际缩放，仅做基础校验。
    """
    image_url = state.get("image_url", "")
    if not image_url:
        logger.error("[vision] preprocess: image_url is empty")
        return {"error_message": "image_url is required"}

    logger.info("[vision] preprocess: image_url=%s", image_url[:60])
    # 初始化控制字段
    return {
        "needs_ocr_retry": False,
        "retry_count":     state.get("retry_count", 0),
        "ocr_results":     [],
        "cot_steps":       [],
        "error_message":   None,
    }


# ---------------------------------------------------------------------------
# 节点 2: build_prompt_node
# ---------------------------------------------------------------------------

def build_prompt_node(state: VisionState) -> dict[str, Any]:
    """
    根据 prompt_mode 选择 Prompt 模板。
    OCR 重试时使用 OCR 增强 Prompt。
    """
    prompt_mode  = state.get("prompt_mode", "standard_visual")
    retry_count  = state.get("retry_count", 0)
    ocr_results  = state.get("ocr_results") or []

    if retry_count > 0 and ocr_results:
        prompt = build_ocr_augmented_prompt(ocr_results)
        logger.info("[vision] build_prompt: using OCR-augmented prompt (retry=%d)", retry_count)
    else:
        prompt = PROMPT_MAP.get(prompt_mode, PROMPT_MAP["standard_visual"])
        logger.info("[vision] build_prompt: mode=%s", prompt_mode)

    return {"current_prompt": prompt}


# ---------------------------------------------------------------------------
# 节点 3: vllm_inference_node（异步）
# ---------------------------------------------------------------------------

async def make_vllm_inference_node(llm_client: BaseLLMClient):
    """
    工厂函数：返回绑定了 llm_client 的节点协程函数。
    用法::

        node = await make_vllm_inference_node(FakeVLLMClient())
        graph.add_node("vllm_inference", node)
    """
    async def vllm_inference_node(state: VisionState) -> dict[str, Any]:
        image_url = state.get("image_url", "")
        prompt    = state.get("current_prompt", "")

        if state.get("error_message"):
            return {}   # 上游已出错，跳过

        logger.info("[vision] vllm_inference: calling LLM...")
        try:
            response = await llm_client.vision_inference(
                image_url=image_url,
                prompt=prompt,
            )
            logger.info(
                "[vision] vllm_inference: done, tokens=%d, latency=%dms",
                response.total_tokens, response.latency_ms,
            )
            return {"raw_llm_output": response.content}
        except Exception as exc:
            logger.error("[vision] vllm_inference failed: %s", exc)
            return {"error_message": str(exc), "raw_llm_output": ""}

    return vllm_inference_node


# ---------------------------------------------------------------------------
# 节点 4: parse_output_node
# ---------------------------------------------------------------------------

def parse_output_node(state: VisionState) -> dict[str, Any]:
    """
    将 VLM 原始输出解析为结构化标号列表。
    强制 JSON 解析；失败则记 error_message（不抛异常）。
    同时提取 CoT 步骤（cot_visual 模式）。
    """
    raw = state.get("raw_llm_output", "")
    if not raw or state.get("error_message"):
        return {"parsed_labels": None}

    # 尝试从输出中提取 JSON 块（LLM 可能在 JSON 前后有多余文字）
    json_str = _extract_json(raw)
    if json_str is None:
        logger.warning("[vision] parse_output: cannot extract JSON from output")
        return {
            "parsed_labels": None,
            "error_message": f"Failed to parse LLM output as JSON: {raw[:200]}",
        }

    try:
        data   = json.loads(json_str)
        labels = data.get("labels", [])
        cot    = data.get("cot_steps", [])
    except json.JSONDecodeError as exc:
        logger.warning("[vision] parse_output: JSON decode error: %s", exc)
        return {
            "parsed_labels": None,
            "error_message": f"JSON decode error: {exc}",
        }

    # 校验每个 label 的 bounding_box（用领域值对象兜住脏数据）
    valid_labels: list[dict[str, Any]] = []
    for label in labels:
        try:
            bb_raw = label.get("bounding_box", {})
            BoundingBox(
                x=bb_raw.get("x", 0.0),
                y=bb_raw.get("y", 0.0),
                width=bb_raw.get("width", 0.1),
                height=bb_raw.get("height", 0.1),
            )
            valid_labels.append(label)
        except Exception as exc:
            logger.warning("[vision] parse_output: invalid bbox for label %s: %s", label.get("label_id"), exc)

    logger.info("[vision] parse_output: %d labels parsed (%d valid)", len(labels), len(valid_labels))
    return {
        "parsed_labels": valid_labels,
        "cot_steps":     cot,   # Annotated[list, operator.add] → 自动追加
    }


def _extract_json(text: str) -> str | None:
    """从可能含有说明文字的 LLM 输出中提取 JSON 字符串。"""
    # 优先找 ```json ... ``` 代码块
    if "```json" in text:
        start = text.index("```json") + 7
        end   = text.index("```", start)
        return text[start:end].strip()
    # 找第一个 { 到最后一个 }
    start = text.find("{")
    end   = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return None


# ---------------------------------------------------------------------------
# 节点 5: confidence_check_node
# ---------------------------------------------------------------------------

def confidence_check_node(state: VisionState) -> dict[str, Any]:
    """
    检查各标号置信度，构建 confidence_scores，
    标记是否需要 OCR 辅助重试。
    """
    labels = state.get("parsed_labels") or []
    if not labels:
        return {"needs_ocr_retry": False, "confidence_scores": {}}

    scores: dict[str, float] = {}
    low_count = 0

    for label in labels:
        lid  = label.get("label_id", "?")
        conf = float(label.get("confidence", 0.0))
        scores[lid] = conf
        if conf < LOW_CONFIDENCE_THRESHOLD:
            low_count += 1
            logger.info(
                "[vision] confidence_check: label %s confidence=%.2f < %.2f (needs OCR)",
                lid, conf, LOW_CONFIDENCE_THRESHOLD,
            )

    retry_count  = state.get("retry_count", 0)
    needs_retry  = low_count > 0 and retry_count < MAX_OCR_RETRIES

    logger.info(
        "[vision] confidence_check: %d labels, %d low-conf, needs_retry=%s",
        len(labels), low_count, needs_retry,
    )
    return {
        "confidence_scores": scores,
        "needs_ocr_retry":   needs_retry,
    }


# ---------------------------------------------------------------------------
# 节点 6: ocr_retry_node
# ---------------------------------------------------------------------------

async def make_ocr_retry_node(ocr_client: Any | None = None):
    """
    工厂函数：返回绑定了 ocr_client 的 OCR 重试节点。
    ocr_client=None 时使用 FakeOCR（返回空结果，不影响主流程测试）。
    """
    async def ocr_retry_node(state: VisionState) -> dict[str, Any]:
        image_url = state.get("image_url", "")
        logger.info("[vision] ocr_retry: running OCR on %s", image_url[:60])

        if ocr_client is not None:
            try:
                ocr_results = await ocr_client.extract(image_url)
            except Exception as exc:
                logger.warning("[vision] ocr_retry: OCR failed: %s, proceeding without OCR", exc)
                ocr_results = []
        else:
            # Fake OCR：返回与图片 URL 匹配的假文字
            ocr_results = [
                {"text": "3",  "score": 0.95, "box": [0.75, 0.40, 0.93, 0.50]},
                {"text": "输出轴", "score": 0.88, "box": [0.75, 0.50, 0.93, 0.60]},
            ]
            logger.info("[vision] ocr_retry: using fake OCR results")

        return {
            "ocr_results": ocr_results,
            "retry_count": state.get("retry_count", 0) + 1,
        }

    return ocr_retry_node


# ---------------------------------------------------------------------------
# 节点 7: finalize_node
# ---------------------------------------------------------------------------

def finalize_node(state: VisionState) -> dict[str, Any]:
    """
    汇总最终结果，转换为 DrawingLabel 友好的结构化字典。
    """
    labels    = state.get("parsed_labels") or []
    scores    = state.get("confidence_scores") or {}
    error_msg = state.get("error_message")

    if error_msg and not labels:
        logger.error("[vision] finalize: no labels due to error: %s", error_msg)
        return {
            "final_result": {
                "success": False,
                "labels":  [],
                "error":   error_msg,
            }
        }

    # 将原始 label dict 转换为含领域值对象信息的结构
    final_labels = []
    for label in labels:
        bb_raw = label.get("bounding_box", {})
        try:
            bbox = BoundingBox(
                x=bb_raw.get("x", 0.0),
                y=bb_raw.get("y", 0.0),
                width=bb_raw.get("width", 0.1),
                height=bb_raw.get("height", 0.1),
            )
            spatial = SpatialInfo.from_bounding_box(bbox, region=label.get("spatial_description", ""))
        except Exception:
            bbox    = None
            spatial = None

        final_labels.append({
            "label_id":           label.get("label_id"),
            "name":               label.get("name"),
            "confidence":         scores.get(label.get("label_id", ""), label.get("confidence", 0.0)),
            "needs_review":       Confidence(value=scores.get(label.get("label_id", ""), 0.0)).needs_review,
            "spatial_description": label.get("spatial_description"),
            "quadrant":           spatial.quadrant.value if spatial else None,
            "bounding_box":       bb_raw,
        })

    result = {
        "success":     True,
        "labels":      final_labels,
        "label_count": len(final_labels),
        "retry_count": state.get("retry_count", 0),
        "cot_steps":   state.get("cot_steps", []),
    }

    logger.info(
        "[vision] finalize: success=%s, labels=%d",
        result["success"], result["label_count"],
    )
    return {"final_result": result}
