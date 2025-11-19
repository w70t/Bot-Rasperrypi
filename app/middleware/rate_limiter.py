"""
Rate Limiting Middleware
Limits API requests per user based on their plan
"""

import time
from fastapi import Request, HTTPException, status
import logging
from typing import Optional
from app.services.cache_service import cache_service
from app.models.user import User
from app.config import get_settings, ERROR_MESSAGES

settings = get_settings()
logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter using Redis for tracking
    """

    @staticmethod
    async def check_rate_limit(user: User) -> tuple[bool, Optional[int]]:
        """
        Check if user has exceeded rate limit

        Args:
            user: User object

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        if not cache_service.redis_client:
            # If Redis is down, allow request (graceful degradation)
            logger.warning("Redis unavailable, bypassing rate limit")
            return True, None

        try:
            key = f"rate_limit:{user.email}"
            current_minute = int(time.time() / 60)
            rate_key = f"{key}:{current_minute}"

            # Get current count
            count = await cache_service.redis_client.get(rate_key)
            current_count = int(count) if count else 0

            # Check limit
            if current_count >= user.rate_limit_per_minute:
                # Calculate retry after
                retry_after = 60 - (int(time.time()) % 60)
                logger.warning(
                    f"Rate limit exceeded for {user.email}: "
                    f"{current_count}/{user.rate_limit_per_minute}"
                )
                return False, retry_after

            # Increment counter
            await cache_service.redis_client.incr(rate_key)
            await cache_service.redis_client.expire(rate_key, 60)

            return True, None

        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            # On error, allow request (graceful degradation)
            return True, None

    @staticmethod
    async def check_usage_quota(user: User) -> tuple[bool, int]:
        """
        Check if user has remaining quota

        Args:
            user: User object

        Returns:
            Tuple of (has_quota, remaining_requests)
        """
        try:
            remaining = user.requests_limit - user.requests_used

            if remaining <= 0:
                logger.warning(
                    f"Quota exceeded for {user.email}: "
                    f"{user.requests_used}/{user.requests_limit}"
                )
                return False, 0

            return True, remaining

        except Exception as e:
            logger.error(f"Error checking usage quota: {str(e)}")
            return True, 0  # Allow on error


# Middleware function
async def enforce_rate_limit(request: Request):
    """
    Enforce rate limiting for authenticated requests

    Args:
        request: FastAPI Request object

    Raises:
        HTTPException if limit exceeded
    """
    # Get user from request state (set by auth middleware)
    user: User = getattr(request.state, "user", None)

    if not user:
        # No user means no auth middleware ran, skip rate limiting
        return

    # Check rate limit
    is_allowed, retry_after = await RateLimiter.check_rate_limit(user)

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"{ERROR_MESSAGES['rate_limit_exceeded']['en']} Retry after {retry_after}s",
            headers={"Retry-After": str(retry_after)},
        )

    # Check usage quota
    has_quota, remaining = await RateLimiter.check_usage_quota(user)

    if not has_quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ERROR_MESSAGES["quota_exceeded"]["en"],
        )

    # Store remaining in request state for response
    request.state.requests_remaining = remaining
