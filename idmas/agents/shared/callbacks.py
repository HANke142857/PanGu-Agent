"""
LangChain 回调处理器。

AgentLoggingCallback：记录每个图节点（chain）的开始/结束/错误，便于排障；
可选把节点耗时上报到 metrics。注入方式：graph.ainvoke(config={"callbacks": [cb]})。

LangFuse 回调见 infrastructure/observability/langfuse_handler.py。
"""
from __future__ import annotations

import logging
import time
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger("idmas.agents")


class AgentLoggingCallback(BaseCallbackHandler):
    """结构化记录节点执行；可选上报 metrics.observe_agent。"""

    def __init__(self, metrics: Any | None = None) -> None:
        self._metrics = metrics
        self._starts: dict[str, float] = {}

    @staticmethod
    def _name(serialized: dict | None, kwargs: dict) -> str:
        if kwargs.get("name"):
            return str(kwargs["name"])
        if serialized:
            return str(serialized.get("name", "chain"))
        return "chain"

    def on_chain_start(self, serialized, inputs, **kwargs):  # noqa: ANN001
        name = self._name(serialized, kwargs)
        self._starts[name] = time.monotonic()
        logger.debug("[agent] ▶ %s", name)

    def on_chain_end(self, outputs, **kwargs):  # noqa: ANN001
        name = self._name(kwargs.get("serialized"), kwargs)
        t0 = self._starts.pop(name, None)
        if t0 is not None:
            elapsed = time.monotonic() - t0
            logger.debug("[agent] ✔ %s (%.3fs)", name, elapsed)
            if self._metrics is not None:
                try:
                    self._metrics.observe_agent(name, elapsed)
                except Exception:  # noqa: BLE001
                    pass

    def on_chain_error(self, error, **kwargs):  # noqa: ANN001
        name = self._name(kwargs.get("serialized"), kwargs)
        self._starts.pop(name, None)
        logger.warning("[agent] x %s 失败: %s", name, error)
