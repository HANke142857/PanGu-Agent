"""
Vision SubGraph 状态定义（LangGraph TypedDict）。

LangGraph 规则：
- 每个节点返回 dict，只包含要更新的字段（partial update）
- Annotated[list, operator.add] → 节点返回的列表与当前列表合并
- 其余字段 → 直接覆盖（last-write-wins）
"""

from __future__ import annotations

import operator
from typing import Annotated, Any

from typing_extensions import TypedDict


class VisionState(TypedDict, total=False):
    # ------------------------------------------------------------------
    # 输入字段（由调用方注入）
    # ------------------------------------------------------------------
    image_url:    str   # 图纸文件 URL（MinIO presigned URL 或 base64）
    prompt_mode:  str   # 'standard_visual' | 'cot_visual' | 'few_shot_visual'
    drawing_id:   str   # 关联图纸 UUID（字符串形式，方便序列化）
    task_id:      str   # 关联任务 UUID

    # ------------------------------------------------------------------
    # 中间状态（节点间传递）
    # ------------------------------------------------------------------
    current_prompt:  str                             # build_prompt_node 构建的 Prompt
    raw_llm_output:  str                             # vllm_inference_node 的原始输出
    ocr_results:     list[dict[str, Any]]            # ocr_retry_node 拿到的 OCR 文字+坐标

    # CoT 步骤（追加语义，用 operator.add 合并）
    cot_steps: Annotated[list[dict[str, Any]], operator.add]

    # ------------------------------------------------------------------
    # 解析结果
    # ------------------------------------------------------------------
    parsed_labels:     list[dict[str, Any]] | None   # parse_output_node 解析出的标号列表
    confidence_scores: dict[str, float] | None       # {label_id: confidence}

    # ------------------------------------------------------------------
    # 控制字段
    # ------------------------------------------------------------------
    needs_ocr_retry: bool   # confidence_check_node 判断是否需要 OCR 辅助重试
    retry_count:     int    # 已重试次数（上限 1 次，超出直接 finalize）

    # ------------------------------------------------------------------
    # 最终输出
    # ------------------------------------------------------------------
    final_result:  dict[str, Any] | None   # finalize_node 输出的结构化结果
    error_message: str | None              # 节点级错误信息
