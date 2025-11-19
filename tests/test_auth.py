"""
Authentication Tests
Comprehensive tests for authentication and authorization (15+ tests)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.auth_service import AuthService, auth_service
from app.models.user import User, UserCreate, PlanType, UserStatus
from app.config import get_settings

settings = get_settings()


# ==================== API KEY GENERATION TESTS ====================

def test_generate_api_key():
    """Test API key generation"""
    api_key = AuthService.generate_api_key()

    assert api_key is not None
    assert api_key.startswith(settings.API_KEY_PREFIX)
    assert len(api_key) > len(settings.API_KEY_PREFIX)


def test_generate_api_key_unique():
    """Test that generated API keys are unique"""
    key1 = AuthService.generate_api_key()
    key2 = AuthService.generate_api_key()

    assert key1 != key2


def test_api_key_format():
    """Test API key has correct format"""
    api_key = AuthService.generate_api_key()

    assert api_key.startswith("tk_")
    # Check that it contains alphanumeric characters
    assert api_key[3:].replace("-", "").replace("_", "").isalnum()


# ==================== API KEY VALIDATION TESTS ====================

def test_hash_api_key():
    """Test API key hashing"""
    api_key = "tk_test_key_123"
    hashed = AuthService.hash_api_key(api_key)

    assert hashed is not None
    assert hashed != api_key
    assert len(hashed) == 64  # SHA256 produces 64 character hex string


def test_hash_api_key_consistent():
    """Test that hashing is consistent"""
    api_key = "tk_test_key_123"
    hash1 = AuthService.hash_api_key(api_key)
    hash2 = AuthService.hash_api_key(api_key)

    assert hash1 == hash2


def test_mask_api_key():
    """Test API key masking for display"""
    api_key = "tk_1234567890abcdef"
    masked = AuthService.mask_api_key(api_key)

    assert "***" in masked
    assert masked.startswith("tk_123")
    assert masked.endswith("cdef")
    assert len(masked) < len(api_key)


def test_mask_short_api_key():
    """Test masking of short API keys"""
    api_key = "tk_abc"
    masked = AuthService.mask_api_key(api_key)

    assert "***" in masked
    assert len(masked) <= len(api_key) + 3


# ==================== USER CREATION TESTS ====================

@pytest.mark.asyncio
async def test_create_user_success(test_user: User):
    """Test successful user creation"""
    user_data = UserCreate(
        email="newuser@example.com",
        plan=PlanType.FREE,
        language="en"
    )

    mock_collection = AsyncMock()
    mock_collection.find_one = AsyncMock(return_value=None)  # No existing user
    mock_collection.insert_one = AsyncMock()

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        user, error = await AuthService.create_user(user_data)

        assert error is None
        assert user is not None
        assert user.email == user_data.email
        assert user.plan == user_data.plan
        assert user.api_key.startswith(settings.API_KEY_PREFIX)
        assert user.referral_code is not None


@pytest.mark.asyncio
async def test_create_user_duplicate_email():
    """Test creating user with existing email"""
    user_data = UserCreate(
        email="existing@example.com",
        plan=PlanType.FREE
    )

    mock_collection = AsyncMock()
    mock_collection.find_one = AsyncMock(return_value={"email": "existing@example.com"})

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        user, error = await AuthService.create_user(user_data)

        assert user is None
        assert error is not None
        assert "already exists" in error


@pytest.mark.asyncio
async def test_create_user_with_referral():
    """Test user creation with referral code"""
    user_data = UserCreate(
        email="referred@example.com",
        plan=PlanType.FREE,
        referred_by="REF123"
    )

    mock_collection = AsyncMock()
    mock_collection.find_one = AsyncMock(return_value=None)
    mock_collection.insert_one = AsyncMock()

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        user, error = await AuthService.create_user(user_data)

        assert error is None
        assert user is not None
        assert user.referred_by == "REF123"


# ==================== USER LOOKUP TESTS ====================

@pytest.mark.asyncio
async def test_get_user_by_api_key_success(test_user: User):
    """Test getting user by valid API key"""
    mock_collection = AsyncMock()
    mock_collection.find_one = AsyncMock(return_value=test_user.dict())

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        user = await AuthService.get_user_by_api_key(test_user.api_key)

        assert user is not None
        assert user.email == test_user.email
        assert user.api_key == test_user.api_key


@pytest.mark.asyncio
async def test_get_user_by_api_key_not_found():
    """Test getting user with non-existent API key"""
    mock_collection = AsyncMock()
    mock_collection.find_one = AsyncMock(return_value=None)

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        user = await AuthService.get_user_by_api_key("tk_nonexistent_key")

        assert user is None


@pytest.mark.asyncio
async def test_get_user_by_email_success(test_user: User):
    """Test getting user by email"""
    mock_collection = AsyncMock()
    mock_collection.find_one = AsyncMock(return_value=test_user.dict())

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        user = await AuthService.get_user_by_email(test_user.email)

        assert user is not None
        assert user.email == test_user.email


@pytest.mark.asyncio
async def test_get_user_by_email_not_found():
    """Test getting user with non-existent email"""
    mock_collection = AsyncMock()
    mock_collection.find_one = AsyncMock(return_value=None)

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        user = await AuthService.get_user_by_email("nonexistent@example.com")

        assert user is None


# ==================== API KEY VALIDATION TESTS ====================

@pytest.mark.asyncio
async def test_validate_api_key_success(test_user: User):
    """Test validation of valid API key"""
    mock_collection = AsyncMock()
    mock_collection.find_one = AsyncMock(return_value=test_user.dict())

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        is_valid, user, error = await AuthService.validate_api_key(test_user.api_key)

        assert is_valid is True
        assert user is not None
        assert error is None


@pytest.mark.asyncio
async def test_validate_api_key_invalid_format():
    """Test validation with invalid format"""
    is_valid, user, error = await AuthService.validate_api_key("invalid_key")

    assert is_valid is False
    assert user is None
    assert error is not None
    assert "format" in error.lower()


@pytest.mark.asyncio
async def test_validate_api_key_not_found():
    """Test validation of non-existent API key"""
    mock_collection = AsyncMock()
    mock_collection.find_one = AsyncMock(return_value=None)

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        is_valid, user, error = await AuthService.validate_api_key("tk_nonexistent_key_123")

        assert is_valid is False
        assert user is None
        assert error is not None


@pytest.mark.asyncio
async def test_validate_api_key_blocked_user(test_user_blocked: User):
    """Test validation of blocked user"""
    mock_collection = AsyncMock()
    mock_collection.find_one = AsyncMock(return_value=test_user_blocked.dict())

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        is_valid, user, error = await AuthService.validate_api_key(test_user_blocked.api_key)

        assert is_valid is False
        assert user is not None
        assert error is not None
        assert "blocked" in error.lower()


@pytest.mark.asyncio
async def test_validate_api_key_expired_subscription(test_user_expired: User):
    """Test validation with expired subscription"""
    mock_collection = AsyncMock()
    mock_collection.find_one = AsyncMock(return_value=test_user_expired.dict())

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        is_valid, user, error = await AuthService.validate_api_key(test_user_expired.api_key)

        assert is_valid is False
        assert user is not None
        assert error is not None
        assert "expired" in error.lower()


@pytest.mark.asyncio
async def test_validate_api_key_inactive_user():
    """Test validation of inactive user"""
    inactive_user = User(
        email="inactive@example.com",
        api_key="tk_inactive_key_123",
        plan=PlanType.FREE,
        status=UserStatus.INACTIVE,
        requests_limit=50,
        rate_limit_per_minute=10
    )

    mock_collection = AsyncMock()
    mock_collection.find_one = AsyncMock(return_value=inactive_user.dict())

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        is_valid, user, error = await AuthService.validate_api_key(inactive_user.api_key)

        assert is_valid is False
        assert user is not None
        assert error is not None


# ==================== USAGE TRACKING TESTS ====================

@pytest.mark.asyncio
async def test_increment_usage_success(test_user: User):
    """Test incrementing user usage counter"""
    mock_result = MagicMock()
    mock_result.modified_count = 1

    mock_collection = AsyncMock()
    mock_collection.update_one = AsyncMock(return_value=mock_result)

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        success = await AuthService.increment_usage(test_user)

        assert success is True
        mock_collection.update_one.assert_called_once()


@pytest.mark.asyncio
async def test_check_usage_quota_available(test_user: User):
    """Test checking usage quota with remaining requests"""
    has_quota, remaining, error = await AuthService.check_usage_quota(test_user)

    assert has_quota is True
    assert remaining > 0
    assert remaining == test_user.requests_limit - test_user.requests_used
    assert error is None


@pytest.mark.asyncio
async def test_check_usage_quota_exceeded(test_user_quota_exceeded: User):
    """Test checking usage quota when exceeded"""
    has_quota, remaining, error = await AuthService.check_usage_quota(test_user_quota_exceeded)

    assert has_quota is False
    assert remaining == 0
    assert error is not None


# ==================== PLAN MANAGEMENT TESTS ====================

@pytest.mark.asyncio
async def test_update_user_plan_success(test_user: User):
    """Test updating user's plan"""
    mock_result = MagicMock()
    mock_result.modified_count = 1

    mock_collection = AsyncMock()
    mock_collection.update_one = AsyncMock(return_value=mock_result)

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        success, error = await AuthService.update_user_plan(test_user.email, PlanType.PRO)

        assert success is True
        assert error is None


@pytest.mark.asyncio
async def test_update_user_plan_invalid_plan():
    """Test updating user with invalid plan"""
    mock_collection = AsyncMock()

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        success, error = await AuthService.update_user_plan("test@example.com", "invalid_plan")

        assert success is False
        assert error is not None


@pytest.mark.asyncio
async def test_update_user_plan_user_not_found():
    """Test updating plan for non-existent user"""
    mock_result = MagicMock()
    mock_result.modified_count = 0

    mock_collection = AsyncMock()
    mock_collection.update_one = AsyncMock(return_value=mock_result)

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        success, error = await AuthService.update_user_plan("nonexistent@example.com", PlanType.PRO)

        assert success is False
        assert error is not None


# ==================== USER BLOCKING TESTS ====================

@pytest.mark.asyncio
async def test_block_user_success(test_user: User):
    """Test blocking a user"""
    mock_result = MagicMock()
    mock_result.modified_count = 1

    mock_collection = AsyncMock()
    mock_collection.update_one = AsyncMock(return_value=mock_result)

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        success, error = await AuthService.block_user(test_user.email, "Spam detected")

        assert success is True
        assert error is None


@pytest.mark.asyncio
async def test_block_user_not_found():
    """Test blocking non-existent user"""
    mock_result = MagicMock()
    mock_result.modified_count = 0

    mock_collection = AsyncMock()
    mock_collection.update_one = AsyncMock(return_value=mock_result)

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        success, error = await AuthService.block_user("nonexistent@example.com", "Test")

        assert success is False
        assert error is not None


@pytest.mark.asyncio
async def test_unblock_user_success(test_user_blocked: User):
    """Test unblocking a user"""
    mock_result = MagicMock()
    mock_result.modified_count = 1

    mock_collection = AsyncMock()
    mock_collection.update_one = AsyncMock(return_value=mock_result)

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        success, error = await AuthService.unblock_user(test_user_blocked.email)

        assert success is True
        assert error is None


# ==================== BATCH OPERATIONS TESTS ====================

@pytest.mark.asyncio
async def test_reset_monthly_usage():
    """Test resetting monthly usage for all users"""
    mock_result = MagicMock()
    mock_result.modified_count = 10

    mock_collection = AsyncMock()
    mock_collection.update_many = AsyncMock(return_value=mock_result)

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        count = await AuthService.reset_monthly_usage()

        assert count == 10
        mock_collection.update_many.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_users():
    """Test getting all users with pagination"""
    mock_users = [
        {"email": "user1@example.com", "api_key": "tk_key1", "plan": "free", "status": "active",
         "requests_used": 0, "requests_limit": 50, "rate_limit_per_minute": 10,
         "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()},
        {"email": "user2@example.com", "api_key": "tk_key2", "plan": "basic", "status": "active",
         "requests_used": 0, "requests_limit": 1000, "rate_limit_per_minute": 30,
         "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()}
    ]

    async def mock_async_iterator():
        for user in mock_users:
            yield user

    mock_cursor = MagicMock()
    mock_cursor.__aiter__ = mock_async_iterator
    mock_cursor.skip = MagicMock(return_value=mock_cursor)
    mock_cursor.limit = MagicMock(return_value=mock_cursor)

    mock_collection = AsyncMock()
    mock_collection.find = MagicMock(return_value=mock_cursor)

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        users = await AuthService.get_all_users(skip=0, limit=10)

        assert len(users) == 2
        assert users[0].email == "user1@example.com"
        assert users[1].email == "user2@example.com"


@pytest.mark.asyncio
async def test_get_user_count():
    """Test getting user count"""
    mock_collection = AsyncMock()
    mock_collection.count_documents = AsyncMock(return_value=100)

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        count = await AuthService.get_user_count()

        assert count == 100


@pytest.mark.asyncio
async def test_get_user_count_with_filters():
    """Test getting user count with filters"""
    mock_collection = AsyncMock()
    mock_collection.count_documents = AsyncMock(return_value=25)

    with patch('app.services.auth_service.Collections.users', return_value=mock_collection):
        count = await AuthService.get_user_count(plan="pro", status="active")

        assert count == 25
        # Verify the query was called with filters
        call_args = mock_collection.count_documents.call_args[0][0]
        assert call_args["plan"] == "pro"
        assert call_args["status"] == "active"
