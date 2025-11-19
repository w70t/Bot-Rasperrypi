"""
Pytest Configuration and Fixtures
Provides reusable test fixtures for the test suite
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from fastapi import FastAPI

# Import app components
from app.main import app
from app.models.user import User, PlanType, UserStatus
from app.config import get_settings
from app.database import Database, Collections
from app.services.cache_service import cache_service


# ==================== EVENT LOOP ====================

@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for the entire test session
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== APP FIXTURES ====================

@pytest.fixture
def test_app() -> FastAPI:
    """
    Get FastAPI application instance
    """
    return app


@pytest.fixture
async def client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """
    Get async HTTP client for testing
    """
    async with AsyncClient(app=test_app, base_url="http://test") as ac:
        yield ac


# ==================== SETTINGS ====================

@pytest.fixture
def settings():
    """
    Get application settings
    """
    return get_settings()


# ==================== DATABASE MOCKS ====================

@pytest.fixture
def mock_db():
    """
    Mock MongoDB database
    """
    db_mock = MagicMock()

    # Mock collections
    users_collection = AsyncMock()
    usage_collection = AsyncMock()
    subscriptions_collection = AsyncMock()

    db_mock.users = users_collection
    db_mock.usage = usage_collection
    db_mock.subscriptions = subscriptions_collection

    return db_mock


@pytest.fixture
def mock_database_connected():
    """
    Mock database connection
    """
    with patch.object(Database, 'client', MagicMock()):
        with patch.object(Database, 'db', MagicMock()):
            yield


# ==================== REDIS/CACHE MOCKS ====================

@pytest.fixture
def mock_redis():
    """
    Mock Redis client
    """
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=True)
    redis_mock.incr = AsyncMock(return_value=1)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.ping = AsyncMock(return_value=True)

    return redis_mock


@pytest.fixture
def mock_cache_service(mock_redis):
    """
    Mock cache service
    """
    with patch.object(cache_service, 'redis_client', mock_redis):
        yield cache_service


# ==================== USER FIXTURES ====================

@pytest.fixture
def test_user() -> User:
    """
    Create a test user with free plan
    """
    return User(
        email="test@example.com",
        api_key="tk_test_key_123456789",
        plan=PlanType.FREE,
        status=UserStatus.ACTIVE,
        requests_used=10,
        requests_limit=50,
        rate_limit_per_minute=10,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        subscription_start=datetime.utcnow(),
        subscription_end=datetime.utcnow() + timedelta(days=30),
        features={
            "video_download": True,
            "basic_metadata": True,
            "country_detection": False,
            "priority_support": False,
            "custom_features": False,
        }
    )


@pytest.fixture
def test_user_basic() -> User:
    """
    Create a test user with basic plan
    """
    return User(
        email="basic@example.com",
        api_key="tk_basic_key_123456789",
        plan=PlanType.BASIC,
        status=UserStatus.ACTIVE,
        requests_used=100,
        requests_limit=1000,
        rate_limit_per_minute=30,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        subscription_start=datetime.utcnow(),
        subscription_end=datetime.utcnow() + timedelta(days=30),
        customer_id="cus_test123",
        subscription_id="sub_test123",
        features={
            "video_download": True,
            "basic_metadata": True,
            "country_detection": False,
            "priority_support": False,
            "custom_features": False,
        }
    )


@pytest.fixture
def test_user_pro() -> User:
    """
    Create a test user with pro plan
    """
    return User(
        email="pro@example.com",
        api_key="tk_pro_key_123456789",
        plan=PlanType.PRO,
        status=UserStatus.ACTIVE,
        requests_used=500,
        requests_limit=10000,
        rate_limit_per_minute=100,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        subscription_start=datetime.utcnow(),
        subscription_end=datetime.utcnow() + timedelta(days=30),
        customer_id="cus_pro123",
        subscription_id="sub_pro123",
        features={
            "video_download": True,
            "basic_metadata": True,
            "country_detection": True,
            "priority_support": True,
            "custom_features": False,
        }
    )


@pytest.fixture
def test_user_blocked() -> User:
    """
    Create a blocked test user
    """
    return User(
        email="blocked@example.com",
        api_key="tk_blocked_key_123456789",
        plan=PlanType.FREE,
        status=UserStatus.SUSPENDED,
        requests_used=0,
        requests_limit=50,
        rate_limit_per_minute=10,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_blocked=True,
        block_reason="Abuse detected"
    )


@pytest.fixture
def test_user_expired() -> User:
    """
    Create a user with expired subscription
    """
    return User(
        email="expired@example.com",
        api_key="tk_expired_key_123456789",
        plan=PlanType.BASIC,
        status=UserStatus.ACTIVE,
        requests_used=0,
        requests_limit=1000,
        rate_limit_per_minute=30,
        created_at=datetime.utcnow() - timedelta(days=60),
        updated_at=datetime.utcnow(),
        subscription_start=datetime.utcnow() - timedelta(days=60),
        subscription_end=datetime.utcnow() - timedelta(days=30),  # Expired
    )


@pytest.fixture
def test_user_quota_exceeded() -> User:
    """
    Create a user who has exceeded their quota
    """
    return User(
        email="quota@example.com",
        api_key="tk_quota_key_123456789",
        plan=PlanType.FREE,
        status=UserStatus.ACTIVE,
        requests_used=50,  # At limit
        requests_limit=50,
        rate_limit_per_minute=10,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        subscription_start=datetime.utcnow(),
        subscription_end=datetime.utcnow() + timedelta(days=30),
    )


# ==================== STRIPE MOCKS ====================

@pytest.fixture
def mock_stripe():
    """
    Mock Stripe API
    """
    with patch('app.services.payment_service.stripe') as stripe_mock:
        # Mock Customer
        customer_mock = MagicMock()
        customer_mock.id = "cus_test123"
        customer_mock.__getitem__ = lambda self, key: {
            'id': 'cus_test123',
            'email': 'test@example.com'
        }.get(key)

        stripe_mock.Customer.create = MagicMock(return_value=customer_mock)
        stripe_mock.Customer.retrieve = MagicMock(return_value=customer_mock)
        stripe_mock.Customer.list = MagicMock(return_value=MagicMock(data=[]))
        stripe_mock.Customer.modify = MagicMock(return_value=customer_mock)

        # Mock Payment Method
        payment_method_mock = MagicMock()
        payment_method_mock.id = "pm_test123"
        stripe_mock.PaymentMethod.attach = MagicMock(return_value=payment_method_mock)

        # Mock Subscription
        subscription_mock = MagicMock()
        subscription_mock.id = "sub_test123"
        subscription_mock.status = "active"
        subscription_mock.current_period_end = int((datetime.utcnow() + timedelta(days=30)).timestamp())
        subscription_mock.current_period_start = int(datetime.utcnow().timestamp())
        subscription_mock.cancel_at_period_end = False
        subscription_mock.canceled_at = None
        subscription_mock.__getitem__ = lambda self, key: {
            'id': 'sub_test123',
            'customer': 'cus_test123',
            'status': 'active',
            'items': {'data': [{'price': {'id': 'price_test123'}}]},
            'current_period_end': int((datetime.utcnow() + timedelta(days=30)).timestamp())
        }.get(key)

        stripe_mock.Subscription.create = MagicMock(return_value=subscription_mock)
        stripe_mock.Subscription.retrieve = MagicMock(return_value=subscription_mock)
        stripe_mock.Subscription.modify = MagicMock(return_value=subscription_mock)

        # Mock Charge
        charge_mock = MagicMock()
        charge_mock.id = "ch_test123"
        charge_mock.amount = 500  # $5.00 in cents
        charge_mock.amount_refunded = 0
        stripe_mock.Charge.list = MagicMock(return_value=MagicMock(data=[charge_mock]))

        # Mock Refund
        refund_mock = MagicMock()
        refund_mock.id = "re_test123"
        refund_mock.amount = 500
        stripe_mock.Refund.create = MagicMock(return_value=refund_mock)

        # Mock Webhook
        webhook_event_mock = MagicMock()
        webhook_event_mock.__getitem__ = lambda self, key: {
            'type': 'customer.subscription.created',
            'data': {'object': subscription_mock}
        }.get(key)
        stripe_mock.Webhook.construct_event = MagicMock(return_value=webhook_event_mock)

        # Mock errors
        stripe_mock.error.CardError = Exception
        stripe_mock.error.StripeError = Exception
        stripe_mock.error.SignatureVerificationError = Exception

        yield stripe_mock


# ==================== TIKTOK SCRAPER MOCKS ====================

@pytest.fixture
def mock_tiktok_response():
    """
    Mock TikTok video extraction response
    """
    return {
        "video_url": "https://example.com/video.mp4",
        "metadata": {
            "video_id": "7123456789",
            "title": "Test TikTok Video",
            "description": "This is a test video",
            "author": "Test User",
            "author_username": "testuser",
            "author_id": "123456",
            "views": 10000,
            "likes": 500,
            "comments": 50,
            "shares": 25,
            "duration": 15,
            "format": "mp4",
            "thumbnail": "https://example.com/thumb.jpg",
            "music": "Test Song",
            "hashtags": ["test", "demo"],
            "created_at": datetime.utcnow().isoformat()
        }
    }


@pytest.fixture
def mock_scraper_service(mock_tiktok_response):
    """
    Mock TikTok scraper service
    """
    async def mock_extract(*args, **kwargs):
        from app.models.video import VideoMetadata
        metadata = VideoMetadata(**mock_tiktok_response["metadata"])
        return mock_tiktok_response["video_url"], metadata, None

    with patch('app.services.scraper_service.extract_tiktok_video', new=mock_extract):
        yield


# ==================== AUTH MOCKS ====================

@pytest.fixture
def mock_auth_service():
    """
    Mock authentication service
    """
    with patch('app.services.auth_service.auth_service') as auth_mock:
        auth_mock.validate_api_key = AsyncMock(return_value=(True, None, None))
        auth_mock.increment_usage = AsyncMock(return_value=True)
        auth_mock.get_user_by_api_key = AsyncMock(return_value=None)
        auth_mock.get_user_by_email = AsyncMock(return_value=None)
        auth_mock.create_user = AsyncMock(return_value=(None, None))
        auth_mock.update_user_plan = AsyncMock(return_value=(True, None))
        auth_mock.block_user = AsyncMock(return_value=(True, None))
        auth_mock.unblock_user = AsyncMock(return_value=(True, None))

        yield auth_mock


# ==================== TELEGRAM/EMAIL MOCKS ====================

@pytest.fixture
def mock_telegram_bot():
    """
    Mock Telegram bot for notifications
    """
    with patch('app.telegram_bot.telegram_bot') as bot_mock:
        bot_mock.send_notification = AsyncMock(return_value=True)
        bot_mock.notify_new_subscriber = AsyncMock(return_value=True)
        bot_mock.notify_error = AsyncMock(return_value=True)

        yield bot_mock


@pytest.fixture
def mock_email_service():
    """
    Mock email service
    """
    with patch('app.utils.email_service.email_service') as email_mock:
        email_mock.send_welcome_email = AsyncMock(return_value=True)
        email_mock.send_payment_failed = AsyncMock(return_value=True)
        email_mock.send_subscription_ended = AsyncMock(return_value=True)
        email_mock.send_upgrade_confirmation = AsyncMock(return_value=True)
        email_mock.send_refund_confirmation = AsyncMock(return_value=True)

        yield email_mock


# ==================== USAGE SERVICE MOCKS ====================

@pytest.fixture
def mock_usage_service():
    """
    Mock usage tracking service
    """
    with patch('app.services.usage_service.usage_service') as usage_mock:
        usage_mock.log_request = AsyncMock(return_value=True)

        yield usage_mock


# ==================== HELPER FUNCTIONS ====================

@pytest.fixture
def valid_tiktok_urls() -> list:
    """
    List of valid TikTok URLs for testing
    """
    return [
        "https://www.tiktok.com/@username/video/1234567890",
        "https://vm.tiktok.com/ZMabcdef/",
        "https://vt.tiktok.com/ZMabcdef/",
        "https://www.tiktok.com/t/ZMabcdef/",
    ]


@pytest.fixture
def invalid_tiktok_urls() -> list:
    """
    List of invalid TikTok URLs for testing
    """
    return [
        "https://youtube.com/watch?v=123",
        "https://instagram.com/p/abc123",
        "not_a_url",
        "",
        "https://tiktok.com",  # Missing video ID
    ]


@pytest.fixture
def auth_headers(test_user: User) -> Dict[str, str]:
    """
    Get authentication headers with API key
    """
    return {
        "X-API-Key": test_user.api_key
    }


@pytest.fixture
def auth_headers_basic(test_user_basic: User) -> Dict[str, str]:
    """
    Get authentication headers for basic user
    """
    return {
        "X-API-Key": test_user_basic.api_key
    }


@pytest.fixture
def auth_headers_pro(test_user_pro: User) -> Dict[str, str]:
    """
    Get authentication headers for pro user
    """
    return {
        "X-API-Key": test_user_pro.api_key
    }


# ==================== CLEANUP ====================

@pytest.fixture(autouse=True)
async def cleanup():
    """
    Cleanup after each test
    """
    yield
    # Cleanup code here if needed
