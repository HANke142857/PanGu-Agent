"""
缓存 + checkpointer 工厂单元测试。
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from idmas.infrastructure.cache import base as cache_base
from idmas.infrastructure.cache.base import InMemoryCacheClient
from idmas.infrastructure.cache.checkpointer import build_checkpointer
from idmas.infrastructure.cache.redis_client import RedisCacheClient


class TestInMemoryCache:
    async def test_set_get_delete(self):
        c = InMemoryCacheClient()
        await c.set("k", "v")
        assert await c.get("k") == "v"
        assert await c.exists("k") is True
        await c.delete("k")
        assert await c.get("k") is None
        assert await c.exists("k") is False

    async def test_ttl_expiry(self, monkeypatch):
        clock = {"t": 1000.0}
        monkeypatch.setattr(cache_base.time, "monotonic", lambda: clock["t"])
        c = InMemoryCacheClient()
        await c.set("k", "v", ttl=10)
        assert await c.get("k") == "v"
        clock["t"] += 11          # 快进越过 TTL
        assert await c.get("k") is None

    async def test_incr_with_ttl(self):
        c = InMemoryCacheClient()
        assert await c.incr_with_ttl("cnt", ttl=60) == 1
        assert await c.incr_with_ttl("cnt", ttl=60) == 2
        assert await c.incr_with_ttl("cnt", ttl=60) == 3

    async def test_list_ops(self):
        c = InMemoryCacheClient()
        await c.lpush("q", "a")
        await c.lpush("q", "b")          # 队列：b a
        assert await c.llen("q") == 2
        assert await c.rpop("q") == "a"  # FIFO
        assert await c.rpop("q") == "b"
        assert await c.rpop("q") is None


class TestRedisClientConstruction:
    def test_construct_without_redis(self):
        c = RedisCacheClient("redis://localhost:6379/0")
        assert c._client is None       # 惰性，未连接


class TestCheckpointerFactory:
    def test_memory_default(self):
        from langgraph.checkpoint.memory import MemorySaver
        cp = build_checkpointer(SimpleNamespace(CHECKPOINTER_BACKEND="memory"))
        assert isinstance(cp, MemorySaver)

    def test_redis_falls_back_when_unavailable(self):
        from langgraph.checkpoint.memory import MemorySaver
        # 包未安装 / 连接失败 → 降级 MemorySaver，不抛异常
        cp = build_checkpointer(SimpleNamespace(
            CHECKPOINTER_BACKEND="redis", REDIS_URL="redis://localhost:6379/0"))
        assert isinstance(cp, MemorySaver)
