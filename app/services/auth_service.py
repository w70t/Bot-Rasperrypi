"""
Authentication Service
Handles API Key generation, validation, and user management
"""

import secrets
import hashlib
import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from app.config import get_settings, PLAN_CONFIGS
from app.database import Collections
from app.models.user import User, UserCreate, PlanType, UserStatus

settings = get_settings()
logger = logging.getLogger(__name__)


class AuthService:
    """
    Authentication and Authorization Service
    Manages API keys and user authentication
    """

    @staticmethod
    def generate_api_key() -> str:
        """
        Generate a secure API key

        Returns:
            API key string (format: tk_xxxxxxxxxxxxx)
        """
        # Generate random secure token
        token = secrets.token_urlsafe(32)

        # Add prefix for identification
        api_key = f"{settings.API_KEY_PREFIX}{token}"

        logger.info(f"Generated new API key: {api_key[:10]}...")

        return api_key

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Hash API key for secure storage

        Args:
            api_key: Plain API key

        Returns:
            Hashed API key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    @staticmethod
    def mask_api_key(api_key: str) -> str:
        """
        Mask API key for logging/display
        Shows only first 6 and last 4 characters

        Args:
            api_key: Plain API key

        Returns:
            Masked API key (e.g., tk_abc***xyz)
        """
        if len(api_key) <= 10:
            return api_key[:3] + "***"

        prefix_len = 6
        suffix_len = 4

        return f"{api_key[:prefix_len]}***{api_key[-suffix_len:]}"

    @staticmethod
    async def create_user(user_data: UserCreate) -> Tuple[Optional[User], Optional[str]]:
        """
        Create a new user with API key

        Args:
            user_data: User creation data

        Returns:
            Tuple of (User object, error_message)
        """
        try:
            # Check if user already exists
            existing_user = await Collections.users().find_one(
                {"email": user_data.email}
            )

            if existing_user:
                return None, "User with this email already exists"

            # Generate API key
            api_key = AuthService.generate_api_key()

            # Get plan configuration
            plan_config = PLAN_CONFIGS.get(user_data.plan, PLAN_CONFIGS["free"])

            # Generate referral code
            referral_code = secrets.token_urlsafe(8)

            # Create user object
            user = User(
                email=user_data.email,
                api_key=api_key,  # Store plain for now, hash in production
                plan=user_data.plan,
                status=UserStatus.ACTIVE,
                requests_limit=plan_config["requests_per_month"],
                rate_limit_per_minute=plan_config["rate_limit_per_minute"],
                features=plan_config["features"],
                language=user_data.language,
                referral_code=referral_code,
                referred_by=user_data.referred_by,
                subscription_start=datetime.utcnow(),
                subscription_end=datetime.utcnow() + timedelta(days=30),
            )

            # Insert into database
            await Collections.users().insert_one(user.dict())

            logger.info(f"Created new user: {user.email} with plan: {user.plan}")

            return user, None

        except Exception as e:
            logger.error(f"Error creating user: {str(e)}", exc_info=True)
            return None, str(e)

    @staticmethod
    async def get_user_by_api_key(api_key: str) -> Optional[User]:
        """
        Get user by API key

        Args:
            api_key: API key to lookup

        Returns:
            User object or None
        """
        try:
            user_data = await Collections.users().find_one({"api_key": api_key})

            if not user_data:
                return None

            return User(**user_data)

        except Exception as e:
            logger.error(f"Error getting user by API key: {str(e)}")
            return None

    @staticmethod
    async def get_user_by_email(email: str) -> Optional[User]:
        """
        Get user by email

        Args:
            email: User email

        Returns:
            User object or None
        """
        try:
            user_data = await Collections.users().find_one({"email": email})

            if not user_data:
                return None

            return User(**user_data)

        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None

    @staticmethod
    async def validate_api_key(api_key: str) -> Tuple[bool, Optional[User], Optional[str]]:
        """
        Validate API key and return user

        Args:
            api_key: API key to validate

        Returns:
            Tuple of (is_valid, user, error_message)
        """
        try:
            # Check format
            if not api_key or not api_key.startswith(settings.API_KEY_PREFIX):
                return False, None, "Invalid API key format"

            # Get user
            user = await AuthService.get_user_by_api_key(api_key)

            if not user:
                return False, None, "Invalid API key"

            # Check if user is active
            if user.status != UserStatus.ACTIVE:
                return False, user, f"Account is {user.status}"

            # Check if user is blocked
            if user.is_blocked:
                return False, user, f"Account blocked: {user.block_reason}"

            # Check subscription expiry
            if user.subscription_end and user.subscription_end < datetime.utcnow():
                return False, user, "Subscription expired"

            # All checks passed
            return True, user, None

        except Exception as e:
            logger.error(f"Error validating API key: {str(e)}", exc_info=True)
            return False, None, "Internal error during validation"

    @staticmethod
    async def check_rate_limit(user: User) -> Tuple[bool, Optional[str]]:
        """
        Check if user has exceeded rate limit

        Args:
            user: User object

        Returns:
            Tuple of (is_allowed, error_message)
        """
        try:
            # This will be implemented in rate_limiting middleware
            # For now, just return True
            # The actual rate limiting logic will use Redis

            return True, None

        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return False, "Error checking rate limit"

    @staticmethod
    async def check_usage_quota(user: User) -> Tuple[bool, int, Optional[str]]:
        """
        Check if user has remaining quota

        Args:
            user: User object

        Returns:
            Tuple of (has_quota, remaining_requests, error_message)
        """
        try:
            remaining = user.requests_limit - user.requests_used

            if remaining <= 0:
                return False, 0, "Monthly quota exceeded"

            return True, remaining, None

        except Exception as e:
            logger.error(f"Error checking usage quota: {str(e)}")
            return False, 0, "Error checking quota"

    @staticmethod
    async def increment_usage(user: User) -> bool:
        """
        Increment user's usage counter

        Args:
            user: User object

        Returns:
            Success status
        """
        try:
            result = await Collections.users().update_one(
                {"email": user.email},
                {
                    "$inc": {"requests_used": 1},
                    "$set": {
                        "last_request_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error incrementing usage: {str(e)}")
            return False

    @staticmethod
    async def update_user_plan(
        email: str,
        new_plan: PlanType
    ) -> Tuple[bool, Optional[str]]:
        """
        Update user's subscription plan

        Args:
            email: User email
            new_plan: New plan type

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get plan configuration
            plan_config = PLAN_CONFIGS.get(new_plan, None)

            if not plan_config:
                return False, "Invalid plan type"

            # Update user
            result = await Collections.users().update_one(
                {"email": email},
                {
                    "$set": {
                        "plan": new_plan,
                        "requests_limit": plan_config["requests_per_month"],
                        "rate_limit_per_minute": plan_config["rate_limit_per_minute"],
                        "features": plan_config["features"],
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            if result.modified_count == 0:
                return False, "User not found or no changes made"

            logger.info(f"Updated user {email} to plan: {new_plan}")

            return True, None

        except Exception as e:
            logger.error(f"Error updating user plan: {str(e)}", exc_info=True)
            return False, str(e)

    @staticmethod
    async def reset_monthly_usage() -> int:
        """
        Reset usage counters for all users (called monthly)

        Returns:
            Number of users reset
        """
        try:
            result = await Collections.users().update_many(
                {},
                {
                    "$set": {
                        "requests_used": 0,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            logger.info(f"Reset monthly usage for {result.modified_count} users")

            return result.modified_count

        except Exception as e:
            logger.error(f"Error resetting monthly usage: {str(e)}")
            return 0

    @staticmethod
    async def block_user(
        email: str,
        reason: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Block a user

        Args:
            email: User email
            reason: Block reason

        Returns:
            Tuple of (success, error_message)
        """
        try:
            result = await Collections.users().update_one(
                {"email": email},
                {
                    "$set": {
                        "is_blocked": True,
                        "block_reason": reason,
                        "status": UserStatus.SUSPENDED,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            if result.modified_count == 0:
                return False, "User not found"

            logger.warning(f"Blocked user {email}: {reason}")

            return True, None

        except Exception as e:
            logger.error(f"Error blocking user: {str(e)}")
            return False, str(e)

    @staticmethod
    async def unblock_user(email: str) -> Tuple[bool, Optional[str]]:
        """
        Unblock a user

        Args:
            email: User email

        Returns:
            Tuple of (success, error_message)
        """
        try:
            result = await Collections.users().update_one(
                {"email": email},
                {
                    "$set": {
                        "is_blocked": False,
                        "block_reason": None,
                        "status": UserStatus.ACTIVE,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            if result.modified_count == 0:
                return False, "User not found"

            logger.info(f"Unblocked user {email}")

            return True, None

        except Exception as e:
            logger.error(f"Error unblocking user: {str(e)}")
            return False, str(e)

    @staticmethod
    async def get_all_users(
        skip: int = 0,
        limit: int = 100,
        plan: Optional[str] = None,
        status: Optional[str] = None
    ) -> list[User]:
        """
        Get all users with optional filters

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            plan: Filter by plan
            status: Filter by status

        Returns:
            List of User objects
        """
        try:
            query = {}

            if plan:
                query["plan"] = plan

            if status:
                query["status"] = status

            cursor = Collections.users().find(query).skip(skip).limit(limit)

            users = []
            async for user_data in cursor:
                users.append(User(**user_data))

            return users

        except Exception as e:
            logger.error(f"Error getting users: {str(e)}")
            return []

    @staticmethod
    async def get_user_count(
        plan: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """
        Get total user count with optional filters

        Args:
            plan: Filter by plan
            status: Filter by status

        Returns:
            User count
        """
        try:
            query = {}

            if plan:
                query["plan"] = plan

            if status:
                query["status"] = status

            count = await Collections.users().count_documents(query)

            return count

        except Exception as e:
            logger.error(f"Error counting users: {str(e)}")
            return 0


# Singleton instance
auth_service = AuthService()
