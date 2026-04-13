from typing import Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from app.config import get_settings

settings = get_settings()

_redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    """Get Redis client instance."""
    global _redis_client
    
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


class RedisCache:
    """Redis cache wrapper with TTL support."""
    
    def __init__(self, prefix: str = "bonebet"):
        self.prefix = prefix
        self._client: Optional[Redis] = None
    
    async def _get_client(self) -> Redis:
        if self._client is None:
            self._client = await get_redis()
        return self._client
    
    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"
    
    async def get(self, key: str) -> Optional[str]:
        client = await self._get_client()
        return await client.get(self._key(key))
    
    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
    ) -> None:
        client = await self._get_client()
        ttl = ttl or settings.REDIS_CACHE_TTL
        await client.setex(self._key(key), ttl, value)
    
    async def delete(self, key: str) -> None:
        client = await self._get_client()
        await client.delete(self._key(key))
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        client = await self._get_client()
        full_pattern = self._key(pattern)
        keys = await client.keys(full_pattern)
        if keys:
            return await client.delete(*keys)
        return 0
    
    async def exists(self, key: str) -> bool:
        client = await self._get_client()
        return await client.exists(self._key(key)) > 0