"""
LangFuse 可观测性处理器（LLM/Agent 链路追踪）。

返回 LangChain CallbackHandler，注入到 LangGraph 的 ainvoke config（callbacks），
即可记录每个 Agent 节点的 prompt/输出/token/延迟。

默认关闭（LANGFUSE_ENABLED=False）→ 返回空回调，零开销。
最佳努力：langfuse 包缺失或初始化失败时返回空回调并告警，不阻断主流程
（自建 LangFuse + OTel 替代 LangSmith SaaS）。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def build_langfuse_callbacks(
    settings: Any,
    *,
    trace_name: str = "idmas",
    user_id: str | None = None,
    session_id: str | None = None,
) -> list:
    """构造 LangFuse 回调列表；未启用/不可用时返回 []。"""
    if not getattr(settings, "LANGFUSE_ENABLED", False):
        return []
    try:
        from langfuse.callback import CallbackHandler  # 惰性导入

        handler = CallbackHandler(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
            trace_name=trace_name,
            user_id=user_id,
            session_id=session_id,
        )
        return [handler]
    except Exception as exc:  # noqa: BLE001 — 追踪是旁路，不可用则降级
        logger.warning("LangFuse 不可用（%s），跳过 LLM 追踪", exc)
        return []
