"""
Redis Caching Service
Handles caching of video data and metadata
"""

import redis.asyncio as redis
import json
import logging
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class CacheService:
    """
    Redis Cache Service
    Manages caching of API responses
    """

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.ttl = settings.REDIS_CACHE_TTL

    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = await redis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                password=settings.REDIS_PASSWORD,
                encoding="utf-8",
                decode_responses=True
            )

            # Test connection
            await self.redis_client.ping()
            logger.info("Successfully connected to Redis")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self.redis_client = None

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached data

        Args:
            key: Cache key

        Returns:
            Cached data or None
        """
        if not self.redis_client:
            return None

        try:
            data = await self.redis_client.get(key)

            if data:
                logger.debug(f"Cache HIT for key: {key}")
                return json.loads(data)

            logger.debug(f"Cache MISS for key: {key}")
            return None

        except Exception as e:
            logger.error(f"Error getting cache: {str(e)}")
            return None

    async def set(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set cached data

        Args:
            key: Cache key
            value: Data to cache
            ttl: Time to live in seconds (default from settings)

        Returns:
            Success status
        """
        if not self.redis_client:
            return False

        try:
            ttl = ttl or self.ttl
            data = json.dumps(value)

            await self.redis_client.setex(key, ttl, data)

            logger.debug(f"Cached data for key: {key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Error setting cache: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete cached data

        Args:
            key: Cache key

        Returns:
            Success status
        """
        if not self.redis_client:
            return False

        try:
            await self.redis_client.delete(key)
            logger.debug(f"Deleted cache for key: {key}")
            return True

        except Exception as e:
            logger.error(f"Error deleting cache: {str(e)}")
            return False

    async def clear_all(self) -> bool:
        """
        Clear all cached data

        Returns:
            Success status
        """
        if not self.redis_client:
            return False

        try:
            await self.redis_client.flushdb()
            logger.warning("Cleared all cache data")
            return True

        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Cache stats dictionary
        """
        if not self.redis_client:
            return {}

        try:
            info = await self.redis_client.info("stats")
            memory = await self.redis_client.info("memory")

            return {
                "connected": True,
                "total_connections": info.get("total_connections_received", 0),
                "total_commands": info.get("total_commands_processed", 0),
                "memory_used_mb": round(memory.get("used_memory", 0) / (1024 * 1024), 2),
                "keys": await self.redis_client.dbsize(),
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {"connected": False}

    def generate_cache_key(self, url: str, extract_country: bool = False) -> str:
        """
        Generate cache key for video URL

        Args:
            url: TikTok video URL
            extract_country: Whether country detection was requested

        Returns:
            Cache key string
        """
        # Simple hash of URL + country flag
        import hashlib
        key_data = f"{url}:{extract_country}"
        hash_value = hashlib.md5(key_data.encode()).hexdigest()
        return f"video:{hash_value}"


# Singleton instance
cache_service = CacheService()
