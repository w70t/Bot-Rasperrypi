# Test Suite Documentation

## Overview

This test suite provides comprehensive coverage of the TikTok Video Intelligence API with **90 complete and working tests**.

## Test Statistics

- **Total Tests**: 90
- **API Tests** (`test_api.py`): 27 tests
- **Authentication Tests** (`test_auth.py`): 33 tests
- **Payment Tests** (`test_payment.py`): 30 tests

## Test Files

### 1. conftest.py
Pytest configuration and fixtures including:
- Event loop configuration
- FastAPI test client
- Mock database connections (MongoDB)
- Mock Redis/cache service
- Test user fixtures (free, basic, pro, blocked, expired, quota exceeded)
- Mock Stripe API
- Mock TikTok scraper service
- Mock authentication service
- Mock Telegram bot and email service
- Helper functions and utilities

### 2. test_api.py (27 tests)
API endpoint tests covering:

#### Health Check Tests (3 tests)
- ✓ Health check with healthy services
- ✓ Health check with degraded services
- ✓ Root endpoint information

#### Video Extraction Tests (21 tests)
- ✓ Successful video extraction
- ✓ Cached video extraction
- ✓ Extraction without API key
- ✓ Extraction with invalid API key
- ✓ Extraction with invalid URL
- ✓ Extraction when quota exceeded
- ✓ Extraction when rate limit exceeded
- ✓ Extraction with metadata enabled
- ✓ Extraction without metadata
- ✓ Country detection forbidden for free plan
- ✓ Country detection allowed for pro plan
- ✓ Extraction when scraping fails
- ✓ Extraction with blocked user
- ✓ Extraction with expired subscription
- ✓ Extraction with empty URL
- ✓ Extraction with malformed JSON
- ✓ Extraction with missing required field
- ✓ Process time tracking
- ✓ Requests remaining tracking
- ✓ Different TikTok URL formats

#### User Endpoint Tests (3 tests)
- ✓ Get user information
- ✓ Create new user
- ✓ Create user with duplicate email
- ✓ Get user usage statistics

### 3. test_auth.py (33 tests)
Authentication and authorization tests covering:

#### API Key Generation (3 tests)
- ✓ API key generation
- ✓ API key uniqueness
- ✓ API key format validation

#### API Key Hashing and Masking (4 tests)
- ✓ API key hashing
- ✓ Hash consistency
- ✓ API key masking for display
- ✓ Short API key masking

#### User Creation (3 tests)
- ✓ Successful user creation
- ✓ Duplicate email rejection
- ✓ User creation with referral code

#### User Lookup (4 tests)
- ✓ Get user by API key (success)
- ✓ Get user by API key (not found)
- ✓ Get user by email (success)
- ✓ Get user by email (not found)

#### API Key Validation (6 tests)
- ✓ Valid API key validation
- ✓ Invalid format rejection
- ✓ Non-existent API key rejection
- ✓ Blocked user rejection
- ✓ Expired subscription rejection
- ✓ Inactive user rejection

#### Usage Tracking (3 tests)
- ✓ Increment usage counter
- ✓ Check usage quota (available)
- ✓ Check usage quota (exceeded)

#### Plan Management (3 tests)
- ✓ Update user plan (success)
- ✓ Invalid plan rejection
- ✓ Non-existent user update

#### User Blocking (3 tests)
- ✓ Block user successfully
- ✓ Block non-existent user
- ✓ Unblock user successfully

#### Batch Operations (4 tests)
- ✓ Reset monthly usage for all users
- ✓ Get all users with pagination
- ✓ Get user count
- ✓ Get user count with filters

### 4. test_payment.py (30 tests)
Payment integration and webhook tests covering:

#### Subscription Creation (4 tests)
- ✓ Create subscription successfully
- ✓ Invalid plan rejection
- ✓ Payment method failure handling
- ✓ Card declined handling

#### Subscription Cancellation (3 tests)
- ✓ Cancel subscription successfully
- ✓ Cancel for non-existent user
- ✓ Cancel when no active subscription

#### Subscription Updates (3 tests)
- ✓ Update subscription successfully
- ✓ Invalid plan rejection
- ✓ Update when no subscription

#### Refund Processing (5 tests)
- ✓ Process full refund (within 7 days)
- ✓ Process partial refund (7-14 days)
- ✓ Refund after expired period
- ✓ Refund with no payment history
- ✓ Custom refund amount

#### Payment Status (2 tests)
- ✓ Check payment status successfully
- ✓ Invalid subscription handling

#### Helper Methods (3 tests)
- ✓ Get or create existing customer
- ✓ Create new customer
- ✓ Get price ID for plans
- ✓ Get plan prices

#### Webhook Handlers (10 tests)
- ✓ Subscription created webhook
- ✓ Missing signature rejection
- ✓ Invalid signature rejection
- ✓ Subscription deleted webhook
- ✓ Payment succeeded webhook
- ✓ Payment failed webhook
- ✓ Charge refunded webhook
- ✓ Unhandled event type
- ✓ Webhook error handling

## Running Tests

### Install Dependencies
```bash
pip install pytest pytest-asyncio pytest-cov httpx
pip install -r requirements.txt
```

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test File
```bash
pytest tests/test_api.py -v
pytest tests/test_auth.py -v
pytest tests/test_payment.py -v
```

### Run Tests with Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### Run Specific Test
```bash
pytest tests/test_api.py::test_extract_video_success -v
```

## Test Coverage

The test suite covers:

### API Endpoints
- ✓ Health check endpoint
- ✓ Root endpoint
- ✓ Video extraction endpoint
- ✓ User management endpoints
- ✓ Webhook endpoints

### Authentication
- ✓ API key generation and validation
- ✓ User creation and lookup
- ✓ Permission checking
- ✓ Account status validation
- ✓ Subscription validation

### Payment Integration
- ✓ Stripe subscription management
- ✓ Payment processing
- ✓ Refund handling
- ✓ Webhook event processing

### Error Handling
- ✓ Invalid input handling
- ✓ Authentication failures
- ✓ Rate limiting
- ✓ Quota exceeded
- ✓ Payment failures
- ✓ External service failures

### Edge Cases
- ✓ Empty values
- ✓ Malformed data
- ✓ Missing required fields
- ✓ Expired subscriptions
- ✓ Blocked users
- ✓ Invalid URLs
- ✓ Different URL formats

## Test Features

### Fixtures
- Comprehensive pytest fixtures for all scenarios
- Mock external services (Stripe, TikTok API, MongoDB, Redis)
- Test user fixtures for different plans and states
- Reusable authentication headers

### Mocking
- Complete Stripe API mocking
- TikTok scraper service mocking
- Database operations mocking
- Cache service mocking
- Email and Telegram notifications mocking

### Test Quality
- Clear test names describing what is being tested
- Docstrings for complex tests
- Proper use of pytest decorators
- Async/await support with pytest-asyncio
- Proper assertion messages

## Coverage Goals

The test suite aims for:
- **80%+ code coverage** overall
- **100% coverage** of critical paths (authentication, payment)
- **All success cases** covered
- **All failure cases** covered
- **Edge cases** properly tested

## Test Organization

Tests are organized by:
1. **Functionality** - Grouped by feature (health, video extraction, auth, payment)
2. **Success/Failure** - Both happy path and error cases
3. **Complexity** - Simple tests first, complex scenarios later

## Continuous Integration

These tests are designed to run in CI/CD pipelines:
- Fast execution (most tests use mocks)
- No external dependencies required
- Deterministic results
- Clear failure messages

## Contributing

When adding new tests:
1. Use existing fixtures from `conftest.py`
2. Follow the naming convention: `test_<feature>_<scenario>`
3. Add docstrings for complex tests
4. Mock external services
5. Test both success and failure cases
6. Keep tests isolated and independent

## Test Maintenance

Regular maintenance tasks:
- Update tests when API changes
- Add tests for new features
- Remove tests for deprecated features
- Update mocks when external APIs change
- Keep coverage above 80%
