"""
Usage Tracking Service
Logs and tracks API usage
"""

import logging
from datetime import datetime
from typing import Optional
from app.database import Collections
from app.models.usage import UsageLog
from app.models.user import User

logger = logging.getLogger(__name__)


class UsageService:
    """
    Usage Tracking and Analytics Service
    """

    @staticmethod
    async def log_request(
        user: User,
        endpoint: str,
        video_url: Optional[str],
        success: bool,
        status_code: int,
        cached: bool,
        response_time_ms: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error: Optional[str] = None,
    ) -> bool:
        """
        Log API request for tracking

        Args:
            user: User object
            endpoint: API endpoint called
            video_url: TikTok video URL
            success: Whether request succeeded
            status_code: HTTP status code
            cached: Whether response was from cache
            response_time_ms: Response time in milliseconds
            ip_address: Client IP address
            user_agent: Client user agent
            error: Error message if failed

        Returns:
            Success status
        """
        try:
            # Mask API key for logging
            from app.services.auth_service import AuthService
            masked_key = AuthService.mask_api_key(user.api_key)

            # Create usage log
            usage_log = UsageLog(
                user_email=user.email,
                api_key=masked_key,
                endpoint=endpoint,
                video_url=video_url,
                success=success,
                status_code=status_code,
                cached=cached,
                response_time_ms=response_time_ms,
                ip_address=ip_address,
                user_agent=user_agent,
                error=error,
                timestamp=datetime.utcnow(),
            )

            # Insert into database
            await Collections.usage().insert_one(usage_log.dict())

            logger.debug(f"Logged request for user: {user.email}")

            return True

        except Exception as e:
            logger.error(f"Error logging request: {str(e)}")
            return False

    @staticmethod
    async def get_user_usage_stats(
        user_email: str,
        days: int = 30
    ) -> dict:
        """
        Get usage statistics for a user

        Args:
            user_email: User email
            days: Number of days to analyze

        Returns:
            Usage statistics dictionary
        """
        try:
            from datetime import timedelta

            start_date = datetime.utcnow() - timedelta(days=days)

            # Aggregate stats
            pipeline = [
                {
                    "$match": {
                        "user_email": user_email,
                        "timestamp": {"$gte": start_date}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_requests": {"$sum": 1},
                        "successful_requests": {
                            "$sum": {"$cond": ["$success", 1, 0]}
                        },
                        "failed_requests": {
                            "$sum": {"$cond": ["$success", 0, 1]}
                        },
                        "cached_requests": {
                            "$sum": {"$cond": ["$cached", 1, 0]}
                        },
                        "avg_response_time": {"$avg": "$response_time_ms"},
                    }
                }
            ]

            cursor = Collections.usage().aggregate(pipeline)
            results = await cursor.to_list(length=1)

            if not results:
                return {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "cached_requests": 0,
                    "avg_response_time": 0,
                }

            stats = results[0]
            stats.pop("_id", None)

            return stats

        except Exception as e:
            logger.error(f"Error getting usage stats: {str(e)}")
            return {}

    @staticmethod
    async def get_system_stats(days: int = 30) -> dict:
        """
        Get system-wide usage statistics

        Args:
            days: Number of days to analyze

        Returns:
            System statistics dictionary
        """
        try:
            from datetime import timedelta

            start_date = datetime.utcnow() - timedelta(days=days)

            # Aggregate system stats
            pipeline = [
                {
                    "$match": {
                        "timestamp": {"$gte": start_date}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_requests": {"$sum": 1},
                        "successful_requests": {
                            "$sum": {"$cond": ["$success", 1, 0]}
                        },
                        "failed_requests": {
                            "$sum": {"$cond": ["$success", 0, 1]}
                        },
                        "cached_requests": {
                            "$sum": {"$cond": ["$cached", 1, 0]}
                        },
                        "avg_response_time": {"$avg": "$response_time_ms"},
                        "unique_users": {"$addToSet": "$user_email"}
                    }
                }
            ]

            cursor = Collections.usage().aggregate(pipeline)
            results = await cursor.to_list(length=1)

            if not results:
                return {}

            stats = results[0]
            stats["active_users"] = len(stats.pop("unique_users", []))
            stats.pop("_id", None)

            return stats

        except Exception as e:
            logger.error(f"Error getting system stats: {str(e)}")
            return {}


# Singleton instance
usage_service = UsageService()
