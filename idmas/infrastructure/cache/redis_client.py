"""
Redis 缓存客户端（生产）。

实现 BaseCacheClient。redis.asyncio 惰性导入——仅实例化并访问时才需要安装，
测试用 InMemoryCacheClient 不受影响。

降级：Redis 不可用时由上层捕获；缓存为旁路优化，不阻断主流程。
Key 规范见技术设计 6.1（task:status / vlm:cache / ratelimit / review:queue …）。
"""

from __future__ import annotations

import logging

from idmas.infrastructure.cache.base import BaseCacheClient

logger = logging.getLogger(__name__)


class RedisCacheClient(BaseCacheClient):
    def __init__(self, url: str) -> None:
        self._url = url
        self._client = None

    def _get_client(self):
        if self._client is None:
            from redis.asyncio import Redis  # 惰性导入

            self._client = Redis.from_url(self._url, decode_responses=True)
        return self._client

    async def get(self, key: str) -> str | None:
        return await self._get_client().get(key)

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        await self._get_client().set(key, value, ex=ttl)

    async def delete(self, key: str) -> None:
        await self._get_client().delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self._get_client().exists(key))

    async def incr_with_ttl(self, key: str, ttl: int) -> int:
        client = self._get_client()
        value = await client.incr(key)
        if value == 1:
            await client.expire(key, ttl)
        return int(value)

    async def lpush(self, key: str, value: str) -> int:
        return int(await self._get_client().lpush(key, value))

    async def rpop(self, key: str) -> str | None:
        return await self._get_client().rpop(key)

    async def llen(self, key: str) -> int:
        return int(await self._get_client().llen(key))

    async def health_check(self) -> bool:
        try:
            return bool(await self._get_client().ping())
        except Exception:  # noqa: BLE001
            return False

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
