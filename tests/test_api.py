"""
API Endpoint Tests
Comprehensive tests for all API endpoints (25+ tests)
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient
from fastapi import status

from app.models.user import User
from app.models.video import VideoExtractRequest, VideoMetadata


# ==================== HEALTH ENDPOINT TESTS ====================

@pytest.mark.asyncio
async def test_health_check_success(client: AsyncClient, mock_database_connected, mock_redis):
    """Test health check endpoint returns healthy status"""
    with patch('app.routers.health.Database.check_health', return_value=True):
        with patch('app.routers.health.cache_service.get_stats', return_value={"connected": True}):
            response = await client.get("/health")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert "version" in data
            assert data["services"]["mongodb"] is True
            assert data["services"]["redis"] is True


@pytest.mark.asyncio
async def test_health_check_degraded(client: AsyncClient):
    """Test health check when services are down"""
    with patch('app.routers.health.Database.check_health', return_value=False):
        with patch('app.routers.health.cache_service.get_stats', return_value={"connected": False}):
            response = await client.get("/health")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "degraded"
            assert data["services"]["mongodb"] is False
            assert data["services"]["redis"] is False


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root endpoint returns API information"""
    response = await client.get("/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "TikTok" in data["message"]


# ==================== VIDEO EXTRACTION TESTS ====================

@pytest.mark.asyncio
async def test_extract_video_success(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict,
    mock_scraper_service,
    mock_usage_service,
    mock_redis
):
    """Test successful video extraction"""
    with patch('app.middleware.auth.auth_service.validate_api_key', return_value=(True, test_user, None)):
        with patch('app.middleware.auth.auth_service.get_user_by_api_key', return_value=test_user):
            with patch('app.services.auth_service.auth_service.increment_usage', return_value=True):
                with patch('app.services.cache_service.cache_service.get', return_value=None):
                    with patch('app.services.cache_service.cache_service.set', return_value=True):
                        response = await client.post(
                            "/api/v1/video/extract",
                            json={"url": "https://www.tiktok.com/@user/video/123"},
                            headers=auth_headers
                        )

                        assert response.status_code == status.HTTP_200_OK
                        data = response.json()
                        assert data["success"] is True
                        assert "video_url" in data
                        assert "metadata" in data
                        assert data["cached"] is False


@pytest.mark.asyncio
async def test_extract_video_cached(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict,
    mock_usage_service,
    mock_redis
):
    """Test video extraction with cache hit"""
    cached_data = {
        "video_url": "https://example.com/video.mp4",
        "metadata": {
            "video_id": "123",
            "title": "Test",
            "author": "User",
            "views": 1000,
            "likes": 100,
            "comments": 10,
            "shares": 5
        }
    }

    with patch('app.middleware.auth.auth_service.validate_api_key', return_value=(True, test_user, None)):
        with patch('app.middleware.auth.auth_service.get_user_by_api_key', return_value=test_user):
            with patch('app.services.auth_service.auth_service.increment_usage', return_value=True):
                with patch('app.services.cache_service.cache_service.get', return_value=cached_data):
                    response = await client.post(
                        "/api/v1/video/extract",
                        json={"url": "https://www.tiktok.com/@user/video/123"},
                        headers=auth_headers
                    )

                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    assert data["success"] is True
                    assert data["cached"] is True
                    assert data["video_url"] == cached_data["video_url"]


@pytest.mark.asyncio
async def test_extract_video_without_api_key(client: AsyncClient):
    """Test video extraction without API key"""
    response = await client.post(
        "/api/v1/video/extract",
        json={"url": "https://www.tiktok.com/@user/video/123"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_extract_video_invalid_api_key(client: AsyncClient):
    """Test video extraction with invalid API key"""
    with patch('app.middleware.auth.auth_service.validate_api_key', return_value=(False, None, "Invalid API key")):
        response = await client.post(
            "/api/v1/video/extract",
            json={"url": "https://www.tiktok.com/@user/video/123"},
            headers={"X-API-Key": "invalid_key"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_extract_video_invalid_url(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict
):
    """Test video extraction with invalid URL"""
    with patch('app.middleware.auth.auth_service.validate_api_key', return_value=(True, test_user, None)):
        with patch('app.middleware.auth.auth_service.get_user_by_api_key', return_value=test_user):
            response = await client.post(
                "/api/v1/video/extract",
                json={"url": "https://youtube.com/watch?v=123"},
                headers=auth_headers
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_extract_video_quota_exceeded(
    client: AsyncClient,
    test_user_quota_exceeded: User,
    mock_redis
):
    """Test video extraction when quota is exceeded"""
    headers = {"X-API-Key": test_user_quota_exceeded.api_key}

    with patch('app.middleware.auth.auth_service.validate_api_key', return_value=(True, test_user_quota_exceeded, None)):
        with patch('app.middleware.auth.auth_service.get_user_by_api_key', return_value=test_user_quota_exceeded):
            response = await client.post(
                "/api/v1/video/extract",
                json={"url": "https://www.tiktok.com/@user/video/123"},
                headers=headers
            )

            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.asyncio
async def test_extract_video_rate_limit_exceeded(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict,
    mock_redis
):
    """Test video extraction when rate limit is exceeded"""
    with patch('app.middleware.auth.auth_service.validate_api_key', return_value=(True, test_user, None)):
        with patch('app.middleware.auth.auth_service.get_user_by_api_key', return_value=test_user):
            with patch('app.middleware.rate_limiter.RateLimiter.check_rate_limit', return_value=(False, 30)):
                response = await client.post(
                    "/api/v1/video/extract",
                    json={"url": "https://www.tiktok.com/@user/video/123"},
                    headers=auth_headers
                )

                assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
                assert "Retry-After" in response.headers


@pytest.mark.asyncio
async def test_extract_video_with_metadata(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict,
    mock_scraper_service,
    mock_usage_service,
    mock_redis
):
    """Test video extraction with metadata enabled"""
    with patch('app.middleware.auth.auth_service.validate_api_key', return_value=(True, test_user, None)):
        with patch('app.middleware.auth.auth_service.get_user_by_api_key', return_value=test_user):
            with patch('app.services.auth_service.auth_service.increment_usage', return_value=True):
                with patch('app.services.cache_service.cache_service.get', return_value=None):
                    with patch('app.services.cache_service.cache_service.set', return_value=True):
                        response = await client.post(
                            "/api/v1/video/extract",
                            json={
                                "url": "https://www.tiktok.com/@user/video/123",
                                "extract_metadata": True
                            },
                            headers=auth_headers
                        )

                        assert response.status_code == status.HTTP_200_OK
                        data = response.json()
                        assert data["success"] is True
                        assert data["metadata"] is not None
                        assert "video_id" in data["metadata"]


@pytest.mark.asyncio
async def test_extract_video_without_metadata(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict,
    mock_scraper_service,
    mock_usage_service,
    mock_redis
):
    """Test video extraction without metadata"""
    with patch('app.middleware.auth.auth_service.validate_api_key', return_value=(True, test_user, None)):
        with patch('app.middleware.auth.auth_service.get_user_by_api_key', return_value=test_user):
            with patch('app.services.auth_service.auth_service.increment_usage', return_value=True):
                with patch('app.services.cache_service.cache_service.get', return_value=None):
                    with patch('app.services.cache_service.cache_service.set', return_value=True):
                        response = await client.post(
                            "/api/v1/video/extract",
                            json={
                                "url": "https://www.tiktok.com/@user/video/123",
                                "extract_metadata": False
                            },
                            headers=auth_headers
                        )

                        assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_extract_video_country_detection_free_plan(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict
):
    """Test country detection is forbidden for free plan"""
    with patch('app.middleware.auth.auth_service.validate_api_key', return_value=(True, test_user, None)):
        with patch('app.middleware.auth.auth_service.get_user_by_api_key', return_value=test_user):
            response = await client.post(
                "/api/v1/video/extract",
                json={
                    "url": "https://www.tiktok.com/@user/video/123",
                    "extract_country": True
                },
                headers=auth_headers
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_extract_video_country_detection_pro_plan(
    client: AsyncClient,
    test_user_pro: User,
    auth_headers_pro: dict,
    mock_scraper_service,
    mock_usage_service,
    mock_redis
):
    """Test country detection is allowed for pro plan"""
    with patch('app.middleware.auth.auth_service.validate_api_key', return_value=(True, test_user_pro, None)):
        with patch('app.middleware.auth.auth_service.get_user_by_api_key', return_value=test_user_pro):
            with patch('app.services.auth_service.auth_service.increment_usage', return_value=True):
                with patch('app.services.cache_service.cache_service.get', return_value=None):
                    with patch('app.services.cache_service.cache_service.set', return_value=True):
                        response = await client.post(
                            "/api/v1/video/extract",
                            json={
                                "url": "https://www.tiktok.com/@user/video/123",
                                "extract_country": True
                            },
                            headers=auth_headers_pro
                        )

                        assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_extract_video_scraping_failure(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict,
    mock_usage_service,
    mock_redis
):
    """Test video extraction when scraping fails"""
    async def mock_extract_failure(*args, **kwargs):
        return None, None, "Failed to extract video"

    with patch('app.middleware.auth.auth_service.validate_api_key', return_value=(True, test_user, None)):
        with patch('app.middleware.auth.auth_service.get_user_by_api_key', return_value=test_user):
            with patch('app.services.auth_service.auth_service.increment_usage', return_value=True):
                with patch('app.services.cache_service.cache_service.get', return_value=None):
                    with patch('app.services.scraper_service.extract_tiktok_video', new=mock_extract_failure):
                        response = await client.post(
                            "/api/v1/video/extract",
                            json={"url": "https://www.tiktok.com/@user/video/123"},
                            headers=auth_headers
                        )

                        assert response.status_code == status.HTTP_200_OK
                        data = response.json()
                        assert data["success"] is False
                        assert "error" in data


@pytest.mark.asyncio
async def test_extract_video_blocked_user(
    client: AsyncClient,
    test_user_blocked: User
):
    """Test video extraction with blocked user"""
    headers = {"X-API-Key": test_user_blocked.api_key}

    with patch('app.middleware.auth.auth_service.validate_api_key',
               return_value=(False, test_user_blocked, f"Account blocked: {test_user_blocked.block_reason}")):
        response = await client.post(
            "/api/v1/video/extract",
            json={"url": "https://www.tiktok.com/@user/video/123"},
            headers=headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_extract_video_expired_subscription(
    client: AsyncClient,
    test_user_expired: User
):
    """Test video extraction with expired subscription"""
    headers = {"X-API-Key": test_user_expired.api_key}

    with patch('app.middleware.auth.auth_service.validate_api_key',
               return_value=(False, test_user_expired, "Subscription expired")):
        response = await client.post(
            "/api/v1/video/extract",
            json={"url": "https://www.tiktok.com/@user/video/123"},
            headers=headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==================== USER ENDPOINT TESTS ====================

@pytest.mark.asyncio
async def test_get_user_info(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict
):
    """Test getting user information"""
    with patch('app.middleware.auth.auth_service.validate_api_key', return_value=(True, test_user, None)):
        with patch('app.middleware.auth.auth_service.get_user_by_api_key', return_value=test_user):
            response = await client.get("/api/v1/user/me", headers=auth_headers)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["email"] == test_user.email
            assert data["plan"] == test_user.plan


@pytest.mark.asyncio
async def test_create_user_success(client: AsyncClient):
    """Test creating a new user"""
    with patch('app.services.auth_service.auth_service.create_user') as mock_create:
        from app.models.user import User, PlanType, UserStatus
        new_user = User(
            email="newuser@example.com",
            api_key="tk_new_key_123",
            plan=PlanType.FREE,
            status=UserStatus.ACTIVE,
            requests_limit=50,
            rate_limit_per_minute=10
        )
        mock_create.return_value = (new_user, None)

        response = await client.post(
            "/api/v1/user/register",
            json={
                "email": "newuser@example.com",
                "plan": "free"
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "api_key" in data
        assert data["email"] == "newuser@example.com"


@pytest.mark.asyncio
async def test_create_user_duplicate_email(client: AsyncClient):
    """Test creating user with duplicate email"""
    with patch('app.services.auth_service.auth_service.create_user') as mock_create:
        mock_create.return_value = (None, "User with this email already exists")

        response = await client.post(
            "/api/v1/user/register",
            json={
                "email": "existing@example.com",
                "plan": "free"
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_get_user_usage_stats(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict
):
    """Test getting user usage statistics"""
    with patch('app.middleware.auth.auth_service.validate_api_key', return_value=(True, test_user, None)):
        with patch('app.middleware.auth.auth_service.get_user_by_api_key', return_value=test_user):
            response = await client.get("/api/v1/user/usage", headers=auth_headers)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "requests_used" in data
            assert "requests_limit" in data
            assert data["requests_used"] == test_user.requests_used


# ==================== EDGE CASE TESTS ====================

@pytest.mark.asyncio
async def test_extract_video_empty_url(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict
):
    """Test video extraction with empty URL"""
    with patch('app.middleware.auth.auth_service.validate_api_key', return_value=(True, test_user, None)):
        with patch('app.middleware.auth.auth_service.get_user_by_api_key', return_value=test_user):
            response = await client.post(
                "/api/v1/video/extract",
                json={"url": ""},
                headers=auth_headers
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_extract_video_malformed_json(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict
):
    """Test video extraction with malformed JSON"""
    with patch('app.middleware.auth.auth_service.validate_api_key', return_value=(True, test_user, None)):
        with patch('app.middleware.auth.auth_service.get_user_by_api_key', return_value=test_user):
            response = await client.post(
                "/api/v1/video/extract",
                content="not valid json",
                headers={**auth_headers, "Content-Type": "application/json"}
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_extract_video_missing_required_field(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict
):
    """Test video extraction with missing required field"""
    with patch('app.middleware.auth.auth_service.validate_api_key', return_value=(True, test_user, None)):
        with patch('app.middleware.auth.auth_service.get_user_by_api_key', return_value=test_user):
            response = await client.post(
                "/api/v1/video/extract",
                json={},
                headers=auth_headers
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_video_extraction_process_time_tracking(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict,
    mock_scraper_service,
    mock_usage_service,
    mock_redis
):
    """Test that process time is tracked in response"""
    with patch('app.middleware.auth.auth_service.validate_api_key', return_value=(True, test_user, None)):
        with patch('app.middleware.auth.auth_service.get_user_by_api_key', return_value=test_user):
            with patch('app.services.auth_service.auth_service.increment_usage', return_value=True):
                with patch('app.services.cache_service.cache_service.get', return_value=None):
                    with patch('app.services.cache_service.cache_service.set', return_value=True):
                        response = await client.post(
                            "/api/v1/video/extract",
                            json={"url": "https://www.tiktok.com/@user/video/123"},
                            headers=auth_headers
                        )

                        assert response.status_code == status.HTTP_200_OK
                        data = response.json()
                        assert "process_time_ms" in data
                        assert isinstance(data["process_time_ms"], int)
                        assert data["process_time_ms"] >= 0


@pytest.mark.asyncio
async def test_requests_remaining_tracking(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict,
    mock_scraper_service,
    mock_usage_service,
    mock_redis
):
    """Test that requests remaining is tracked correctly"""
    with patch('app.middleware.auth.auth_service.validate_api_key', return_value=(True, test_user, None)):
        with patch('app.middleware.auth.auth_service.get_user_by_api_key', return_value=test_user):
            with patch('app.services.auth_service.auth_service.increment_usage', return_value=True):
                with patch('app.services.cache_service.cache_service.get', return_value=None):
                    with patch('app.services.cache_service.cache_service.set', return_value=True):
                        with patch('app.middleware.rate_limiter.RateLimiter.check_usage_quota',
                                   return_value=(True, 40)):
                            response = await client.post(
                                "/api/v1/video/extract",
                                json={"url": "https://www.tiktok.com/@user/video/123"},
                                headers=auth_headers
                            )

                            assert response.status_code == status.HTTP_200_OK
                            data = response.json()
                            assert "requests_remaining" in data


@pytest.mark.asyncio
async def test_different_tiktok_url_formats(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict,
    mock_scraper_service,
    mock_usage_service,
    mock_redis,
    valid_tiktok_urls: list
):
    """Test extraction with different TikTok URL formats"""
    for url in valid_tiktok_urls:
        with patch('app.middleware.auth.auth_service.validate_api_key', return_value=(True, test_user, None)):
            with patch('app.middleware.auth.auth_service.get_user_by_api_key', return_value=test_user):
                with patch('app.services.auth_service.auth_service.increment_usage', return_value=True):
                    with patch('app.services.cache_service.cache_service.get', return_value=None):
                        with patch('app.services.cache_service.cache_service.set', return_value=True):
                            response = await client.post(
                                "/api/v1/video/extract",
                                json={"url": url},
                                headers=auth_headers
                            )

                            assert response.status_code == status.HTTP_200_OK
