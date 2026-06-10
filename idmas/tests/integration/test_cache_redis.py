"""
RedisCacheClient 真实集成测试（连本地 Redis）。

需要本地 Redis（如 docker compose 的 idmas-redis-1，localhost:6379）。
连不上则整组跳过——不在 CI/无 Redis 环境下误报。
"""

from __future__ import annotations

import uuid

import pytest

from idmas.infrastructure.cache.redis_client import RedisCacheClient

REDIS_URL = "redis://localhost:6379/0"


@pytest.fixture()
async def redis_client():
    client = RedisCacheClient(REDIS_URL)
    if not await client.health_check():
        await client.close()
        pytest.skip("本地 Redis 不可用，跳过 Redis 集成测试")
    yield client
    await client.close()


@pytest.fixture()
def k():
    return f"idmastest:{uuid.uuid4()}"


class TestRedisRoundtrip:
    async def test_set_get_delete(self, redis_client, k):
        await redis_client.set(k, "hello", ttl=30)
        assert await redis_client.get(k) == "hello"
        assert await redis_client.exists(k) is True
        await redis_client.delete(k)
        assert await redis_client.get(k) is None

    async def test_incr_with_ttl(self, redis_client, k):
        try:
            assert await redis_client.incr_with_ttl(k, ttl=30) == 1
            assert await redis_client.incr_with_ttl(k, ttl=30) == 2
        finally:
            await redis_client.delete(k)

    async def test_list_ops(self, redis_client, k):
        try:
            await redis_client.lpush(k, "a")
            await redis_client.lpush(k, "b")
            assert await redis_client.llen(k) == 2
            assert await redis_client.rpop(k) == "a"   # FIFO
        finally:
            await redis_client.delete(k)
