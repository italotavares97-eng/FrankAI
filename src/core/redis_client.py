"""Frank AI OS — Cliente Redis para cache, filas e pub/sub."""

import json
from typing import Any, Optional
import redis.asyncio as aioredis

from app.core.config import settings


_redis_pool: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
    return _redis_pool


class CacheService:
    """Serviço de cache com prefixo por domínio."""

    def __init__(self, prefix: str = "frank"):
        self.prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        redis = await get_redis()
        value = await redis.get(self._key(key))
        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: Any, ttl: int = settings.cache_ttl) -> None:
        redis = await get_redis()
        await redis.setex(self._key(key), ttl, json.dumps(value, default=str))

    async def delete(self, key: str) -> None:
        redis = await get_redis()
        await redis.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        redis = await get_redis()
        return bool(await redis.exists(self._key(key)))

    async def invalidate_pattern(self, pattern: str) -> int:
        redis = await get_redis()
        keys = await redis.keys(f"{self.prefix}:{pattern}")
        if keys:
            return await redis.delete(*keys)
        return 0


class AlertQueue:
    """Fila de alertas em tempo real via Redis pub/sub."""

    CHANNEL = "frank:alerts"

    async def publish(self, alert: dict) -> None:
        redis = await get_redis()
        await redis.publish(self.CHANNEL, json.dumps(alert, default=str))

    async def push_to_list(self, alert: dict) -> None:
        redis = await get_redis()
        await redis.lpush("frank:alert_list", json.dumps(alert, default=str))
        await redis.ltrim("frank:alert_list", 0, 999)  # keep last 1000

    async def get_recent(self, count: int = 20) -> list:
        redis = await get_redis()
        items = await redis.lrange("frank:alert_list", 0, count - 1)
        return [json.loads(i) for i in items]


# Instâncias globais
cache = CacheService()
alert_queue = AlertQueue()
