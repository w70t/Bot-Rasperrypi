"""
Video API Endpoints
Main endpoint for video extraction
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
import time
import logging
from app.models.video import VideoExtractRequest, VideoExtractResponse, VideoMetadata
from app.models.user import User
from app.middleware.auth import verify_api_key
from app.middleware.rate_limiter import enforce_rate_limit
from app.services.scraper_service import extract_tiktok_video
from app.services.cache_service import cache_service
from app.services.auth_service import auth_service
from app.services.usage_service import usage_service
from app.config import get_settings, ERROR_MESSAGES

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/video", tags=["video"])


@router.post("/extract", response_model=VideoExtractResponse)
async def extract_video(
    request: Request,
    extract_request: VideoExtractRequest,
    user: User = Depends(verify_api_key),
):
    """
    Extract TikTok video and metadata

    Args:
        request: FastAPI request
        extract_request: Extraction request body
        user: Authenticated user

    Returns:
        VideoExtractResponse with video URL and metadata
    """
    start_time = time.time()

    try:
        # Enforce rate limit
        await enforce_rate_limit(request)

        url = extract_request.url
        extract_metadata = extract_request.extract_metadata
        extract_country = extract_request.extract_country

        # Check if country detection is allowed for this plan
        if extract_country and not user.features.get("country_detection", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Country detection is only available for Pro and Business plans"
            )

        # Generate cache key
        cache_key = cache_service.generate_cache_key(url, extract_country)

        # Try to get from cache
        cached_data = await cache_service.get(cache_key)

        if cached_data:
            logger.info(f"Cache HIT for {url}")

            # Log request
            response_time = int((time.time() - start_time) * 1000)
            await usage_service.log_request(
                user=user,
                endpoint="/api/v1/video/extract",
                video_url=url,
                success=True,
                status_code=200,
                cached=True,
                response_time_ms=response_time,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )

            # Increment usage (even for cached requests)
            await auth_service.increment_usage(user)

            # Prepare response
            metadata = VideoMetadata(**cached_data["metadata"]) if cached_data.get("metadata") else None

            return VideoExtractResponse(
                success=True,
                video_url=cached_data["video_url"],
                metadata=metadata,
                cached=True,
                requests_remaining=getattr(request.state, "requests_remaining", 0),
                process_time_ms=response_time,
            )

        # Cache miss - extract video
        logger.info(f"Cache MISS for {url} - extracting...")

        video_url, metadata, error = await extract_tiktok_video(
            url,
            extract_metadata=extract_metadata,
        )

        response_time = int((time.time() - start_time) * 1000)

        if not video_url:
            # Extraction failed
            logger.error(f"Extraction failed for {url}: {error}")

            # Log failed request
            await usage_service.log_request(
                user=user,
                endpoint="/api/v1/video/extract",
                video_url=url,
                success=False,
                status_code=400,
                cached=False,
                response_time_ms=response_time,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                error=error,
            )

            # Still increment usage for failed requests
            await auth_service.increment_usage(user)

            return VideoExtractResponse(
                success=False,
                error=error or "Failed to extract video",
                requests_remaining=getattr(request.state, "requests_remaining", 0),
                process_time_ms=response_time,
            )

        # Extraction successful
        logger.info(f"Successfully extracted video from {url}")

        # Cache the result
        cache_data = {
            "video_url": video_url,
            "metadata": metadata.dict() if metadata else None,
            "cached_at": time.time(),
        }
        await cache_service.set(cache_key, cache_data)

        # Log successful request
        await usage_service.log_request(
            user=user,
            endpoint="/api/v1/video/extract",
            video_url=url,
            success=True,
            status_code=200,
            cached=False,
            response_time_ms=response_time,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        # Increment usage
        await auth_service.increment_usage(user)

        # Prepare response
        return VideoExtractResponse(
            success=True,
            video_url=video_url,
            metadata=metadata,
            cached=False,
            requests_remaining=getattr(request.state, "requests_remaining", 0),
            process_time_ms=response_time,
        )

    except HTTPException:
        # Re-raise HTTP exceptions (rate limit, auth, etc.)
        raise

    except Exception as e:
        logger.error(f"Unexpected error in extract_video: {str(e)}", exc_info=True)

        response_time = int((time.time() - start_time) * 1000)

        # Log error
        await usage_service.log_request(
            user=user,
            endpoint="/api/v1/video/extract",
            video_url=extract_request.url,
            success=False,
            status_code=500,
            cached=False,
            response_time_ms=response_time,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            error=str(e),
        )

        return VideoExtractResponse(
            success=False,
            error=ERROR_MESSAGES["server_error"]["en"],
            detail=str(e) if settings.DEBUG else None,
            requests_remaining=getattr(request.state, "requests_remaining", 0),
            process_time_ms=response_time,
        )
