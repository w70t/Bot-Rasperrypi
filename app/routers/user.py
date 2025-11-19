"""
User Management Endpoints
For user registration and account management
"""

from fastapi import APIRouter, Depends, HTTPException, status
import logging
from app.models.user import UserCreate, User, UserResponse
from app.services.auth_service import auth_service
from app.middleware.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/user", tags=["user"])


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate):
    """
    Register a new user

    Args:
        user_data: User registration data

    Returns:
        User info with API key
    """
    try:
        user, error = await auth_service.create_user(user_data)

        if error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )

        logger.info(f"New user registered: {user.email}")

        return {
            "success": True,
            "message": "User created successfully",
            "api_key": user.api_key,
            "email": user.email,
            "plan": user.plan,
            "requests_limit": user.requests_limit,
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error registering user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(user: User = Depends(verify_api_key)):
    """
    Get current user info

    Args:
        user: Authenticated user

    Returns:
        User information
    """
    return UserResponse(
        email=user.email,
        plan=user.plan,
        status=user.status,
        requests_used=user.requests_used,
        requests_limit=user.requests_limit,
        subscription_end=user.subscription_end,
        created_at=user.created_at,
    )


@router.get("/usage", response_model=dict)
async def get_usage_stats(user: User = Depends(verify_api_key)):
    """
    Get usage statistics for current user

    Args:
        user: Authenticated user

    Returns:
        Usage statistics
    """
    from app.services.usage_service import usage_service

    stats = await usage_service.get_user_usage_stats(user.email, days=30)

    return {
        "email": user.email,
        "plan": user.plan,
        "current_usage": {
            "requests_used": user.requests_used,
            "requests_limit": user.requests_limit,
            "usage_percentage": round((user.requests_used / user.requests_limit) * 100, 1),
            "requests_remaining": user.requests_limit - user.requests_used,
        },
        "monthly_stats": stats,
    }
