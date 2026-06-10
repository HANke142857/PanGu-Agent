"""
缓存抽象。

与项目其它基础设施一致（抽象接口 + Fake + 真实实现）::

    BaseCacheClient     : 抽象接口
    InMemoryCacheClient : 测试/开发用，进程内 dict + 惰性 TTL（无需 Redis）
    RedisCacheClient    : 生产实现，见 redis_client.py（需 Redis）

用途：任务状态缓存、vLLM 结果缓存、API 限流计数、人工审核/重试队列。
Key 规范见技术设计 6.1。
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections import deque


class BaseCacheClient(ABC):
    @abstractmethod
    async def get(self, key: str) -> str | None:
        ...

    @abstractmethod
    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        ...

    @abstractmethod
    async def incr_with_ttl(self, key: str, ttl: int) -> int:
        """自增计数，首次设置 TTL（API 限流用）。返回自增后的值。"""
        ...

    @abstractmethod
    async def lpush(self, key: str, value: str) -> int:
        ...

    @abstractmethod
    async def rpop(self, key: str) -> str | None:
        ...

    @abstractmethod
    async def llen(self, key: str) -> int:
        ...

    async def health_check(self) -> bool:
        return True

    async def close(self) -> None:
        return None


class InMemoryCacheClient(BaseCacheClient):
    """进程内缓存：dict + 惰性过期。"""

    def __init__(self) -> None:
        self._kv: dict[str, tuple[str, float | None]] = {}     # key -> (value, expire_at)
        self._lists: dict[str, deque[str]] = {}

    def _expired(self, key: str) -> bool:
        item = self._kv.get(key)
        if item is None:
            return True
        _, expire_at = item
        if expire_at is not None and time.monotonic() >= expire_at:
            self._kv.pop(key, None)
            return True
        return False

    async def get(self, key: str) -> str | None:
        if self._expired(key):
            return None
        return self._kv[key][0]

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        expire_at = (time.monotonic() + ttl) if ttl else None
        self._kv[key] = (value, expire_at)

    async def delete(self, key: str) -> None:
        self._kv.pop(key, None)
        self._lists.pop(key, None)

    async def exists(self, key: str) -> bool:
        return not self._expired(key)

    async def incr_with_ttl(self, key: str, ttl: int) -> int:
        current = 0 if self._expired(key) else int(self._kv[key][0])
        current += 1
        # 仅首次（计数从 1 开始）设置过期窗口
        expire_at = self._kv[key][1] if (key in self._kv and current > 1) else time.monotonic() + ttl
        self._kv[key] = (str(current), expire_at)
        return current

    async def lpush(self, key: str, value: str) -> int:
        dq = self._lists.setdefault(key, deque())
        dq.appendleft(value)
        return len(dq)

    async def rpop(self, key: str) -> str | None:
        dq = self._lists.get(key)
        if not dq:
            return None
        return dq.pop()

    async def llen(self, key: str) -> int:
        return len(self._lists.get(key, ()))
