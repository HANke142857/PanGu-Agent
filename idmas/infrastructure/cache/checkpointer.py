"""
LangGraph Checkpointer 工厂。

  - memory（默认）：MemorySaver，进程内，重启丢失
  - redis：langgraph-checkpoint-redis（需额外安装），Agent 状态跨进程/重启持久化

redis 为最佳努力：依赖包缺失或初始化失败时降级为 MemorySaver 并告警，
保证 worker 不因 checkpointer 而崩溃（技术设计 6.1 的降级策略）。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def build_checkpointer(settings: Any) -> Any:
    """按 settings.CHECKPOINTER_BACKEND 返回 LangGraph checkpointer。"""
    from langgraph.checkpoint.memory import MemorySaver

    backend = getattr(settings, "CHECKPOINTER_BACKEND", "memory")
    if backend != "redis":
        return MemorySaver()

    try:
        from langgraph.checkpoint.redis import RedisSaver  # 需 langgraph-checkpoint-redis

        saver = RedisSaver.from_conn_string(settings.REDIS_URL)
        # 部分版本返回上下文管理器；统一取出真实 saver 并 setup
        if hasattr(saver, "__enter__"):
            saver = saver.__enter__()
        if hasattr(saver, "setup"):
            saver.setup()
        logger.info("使用 Redis LangGraph Checkpointer")
        return saver
    except Exception as exc:  # noqa: BLE001 — 降级保证不崩
        logger.warning("Redis Checkpointer 不可用（%s），降级为 MemorySaver", exc)
        return MemorySaver()
