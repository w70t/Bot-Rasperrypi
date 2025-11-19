"""
Authentication Middleware
Validates API keys for protected endpoints
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import logging
from app.services.auth_service import auth_service
from app.config import get_settings, ERROR_MESSAGES

settings = get_settings()
logger = logging.getLogger(__name__)


async def verify_api_key(request: Request):
    """
    Verify API key from request headers

    Args:
        request: FastAPI Request object

    Returns:
        User object if valid

    Raises:
        HTTPException if invalid
    """
    # Get API key from header
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        logger.warning("Request without API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES["invalid_api_key"]["en"],
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validate API key
    is_valid, user, error_msg = await auth_service.validate_api_key(api_key)

    if not is_valid:
        logger.warning(f"Invalid API key attempt: {api_key[:10]}... - {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_msg or ERROR_MESSAGES["invalid_api_key"]["en"],
        )

    # Attach user to request state
    request.state.user = user

    logger.debug(f"Authenticated user: {user.email}")

    return user
