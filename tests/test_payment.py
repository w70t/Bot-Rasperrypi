"""
Payment and Webhook Tests
Comprehensive tests for Stripe payment integration (10+ tests)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient
from fastapi import status

from app.services.payment_service import PaymentService, payment_service
from app.models.user import User, PlanType


# ==================== SUBSCRIPTION CREATION TESTS ====================

@pytest.mark.asyncio
async def test_create_subscription_success(test_user: User, mock_stripe, mock_telegram_bot, mock_email_service):
    """Test successful subscription creation"""
    with patch('app.services.auth_service.auth_service.update_user_subscription', return_value=None):
        with patch('app.services.auth_service.auth_service.get_user_by_email', return_value=test_user):
            success, error, subscription_data = await payment_service.create_subscription(
                email=test_user.email,
                plan="basic",
                payment_method="pm_test123"
            )

            assert success is True
            assert error is None
            assert subscription_data is not None
            assert subscription_data["subscription_id"] == "sub_test123"
            assert subscription_data["customer_id"] == "cus_test123"


@pytest.mark.asyncio
async def test_create_subscription_invalid_plan(test_user: User, mock_stripe):
    """Test subscription creation with invalid plan"""
    success, error, subscription_data = await payment_service.create_subscription(
        email=test_user.email,
        plan="invalid_plan",
        payment_method="pm_test123"
    )

    assert success is False
    assert error is not None
    assert "Invalid plan" in error
    assert subscription_data is None


@pytest.mark.asyncio
async def test_create_subscription_payment_method_failure(test_user: User, mock_stripe):
    """Test subscription creation with payment method failure"""
    mock_stripe.PaymentMethod.attach.side_effect = Exception("Payment method error")

    success, error, subscription_data = await payment_service.create_subscription(
        email=test_user.email,
        plan="basic",
        payment_method="pm_invalid"
    )

    assert success is False
    assert error is not None
    assert subscription_data is None


@pytest.mark.asyncio
async def test_create_subscription_card_declined(test_user: User, mock_stripe):
    """Test subscription creation with declined card"""
    mock_stripe.error.CardError = Exception
    mock_stripe.Subscription.create.side_effect = Exception("Card declined")

    success, error, subscription_data = await payment_service.create_subscription(
        email=test_user.email,
        plan="basic",
        payment_method="pm_test123"
    )

    assert success is False
    assert error is not None


# ==================== SUBSCRIPTION CANCELLATION TESTS ====================

@pytest.mark.asyncio
async def test_cancel_subscription_success(test_user_basic: User, mock_stripe, mock_telegram_bot, mock_email_service):
    """Test successful subscription cancellation"""
    with patch('app.services.auth_service.auth_service.get_user_by_email', return_value=test_user_basic):
        with patch('app.services.auth_service.auth_service.update_user_subscription', return_value=None):
            success, error = await payment_service.cancel_subscription(
                user_email=test_user_basic.email,
                reason="User requested"
            )

            assert success is True
            assert error is None


@pytest.mark.asyncio
async def test_cancel_subscription_user_not_found(mock_stripe):
    """Test cancellation for non-existent user"""
    with patch('app.services.auth_service.auth_service.get_user_by_email', return_value=None):
        success, error = await payment_service.cancel_subscription(
            user_email="nonexistent@example.com",
            reason="Test"
        )

        assert success is False
        assert error is not None
        assert "not found" in error


@pytest.mark.asyncio
async def test_cancel_subscription_no_active_subscription(test_user: User, mock_stripe):
    """Test cancellation when user has no active subscription"""
    with patch('app.services.auth_service.auth_service.get_user_by_email', return_value=test_user):
        success, error = await payment_service.cancel_subscription(
            user_email=test_user.email,
            reason="Test"
        )

        assert success is False
        assert error is not None
        assert "No active subscription" in error


# ==================== SUBSCRIPTION UPDATE TESTS ====================

@pytest.mark.asyncio
async def test_update_subscription_success(test_user_basic: User, mock_stripe, mock_telegram_bot, mock_email_service):
    """Test successful subscription upgrade"""
    with patch('app.services.auth_service.auth_service.get_user_by_email', return_value=test_user_basic):
        with patch('app.services.auth_service.auth_service.update_user_plan', return_value=(True, None)):
            success, error = await payment_service.update_subscription(
                user_email=test_user_basic.email,
                new_plan="pro"
            )

            assert success is True
            assert error is None


@pytest.mark.asyncio
async def test_update_subscription_invalid_plan(test_user_basic: User, mock_stripe):
    """Test subscription update with invalid plan"""
    with patch('app.services.auth_service.auth_service.get_user_by_email', return_value=test_user_basic):
        success, error = await payment_service.update_subscription(
            user_email=test_user_basic.email,
            new_plan="invalid_plan"
        )

        assert success is False
        assert error is not None
        assert "Invalid plan" in error


@pytest.mark.asyncio
async def test_update_subscription_no_active_subscription(test_user: User, mock_stripe):
    """Test update when user has no subscription"""
    with patch('app.services.auth_service.auth_service.get_user_by_email', return_value=test_user):
        success, error = await payment_service.update_subscription(
            user_email=test_user.email,
            new_plan="pro"
        )

        assert success is False
        assert error is not None
        assert "No active subscription" in error


# ==================== REFUND TESTS ====================

@pytest.mark.asyncio
async def test_process_refund_full_refund(test_user_basic: User, mock_stripe, mock_telegram_bot, mock_email_service):
    """Test processing full refund within 7 days"""
    # Set created_at to 5 days ago
    test_user_basic.created_at = datetime.utcnow() - timedelta(days=5)

    with patch('app.services.auth_service.auth_service.get_user_by_email', return_value=test_user_basic):
        with patch('app.services.auth_service.auth_service.update_user_subscription', return_value=None):
            success, error = await payment_service.process_refund(
                user_email=test_user_basic.email,
                reason="requested_by_customer"
            )

            assert success is True
            assert error is None


@pytest.mark.asyncio
async def test_process_refund_partial_refund(test_user_basic: User, mock_stripe, mock_telegram_bot, mock_email_service):
    """Test processing partial refund between 7-14 days"""
    # Set created_at to 10 days ago
    test_user_basic.created_at = datetime.utcnow() - timedelta(days=10)

    with patch('app.services.auth_service.auth_service.get_user_by_email', return_value=test_user_basic):
        with patch('app.services.auth_service.auth_service.update_user_subscription', return_value=None):
            success, error = await payment_service.process_refund(
                user_email=test_user_basic.email,
                reason="requested_by_customer"
            )

            assert success is True
            assert error is None


@pytest.mark.asyncio
async def test_process_refund_expired_period(test_user_basic: User, mock_stripe):
    """Test refund request after 14 days"""
    # Set created_at to 20 days ago
    test_user_basic.created_at = datetime.utcnow() - timedelta(days=20)

    with patch('app.services.auth_service.auth_service.get_user_by_email', return_value=test_user_basic):
        success, error = await payment_service.process_refund(
            user_email=test_user_basic.email,
            reason="requested_by_customer"
        )

        assert success is False
        assert error is not None
        assert "expired" in error.lower()


@pytest.mark.asyncio
async def test_process_refund_no_payment_history(test_user: User, mock_stripe):
    """Test refund for user with no payment history"""
    with patch('app.services.auth_service.auth_service.get_user_by_email', return_value=test_user):
        success, error = await payment_service.process_refund(
            user_email=test_user.email,
            reason="requested_by_customer"
        )

        assert success is False
        assert error is not None
        assert "payment history" in error.lower()


@pytest.mark.asyncio
async def test_process_refund_custom_amount(test_user_basic: User, mock_stripe, mock_telegram_bot, mock_email_service):
    """Test processing refund with custom amount"""
    test_user_basic.created_at = datetime.utcnow() - timedelta(days=5)

    with patch('app.services.auth_service.auth_service.get_user_by_email', return_value=test_user_basic):
        with patch('app.services.auth_service.auth_service.update_user_subscription', return_value=None):
            success, error = await payment_service.process_refund(
                user_email=test_user_basic.email,
                amount=2.50,  # Custom amount
                reason="requested_by_customer"
            )

            assert success is True
            assert error is None


# ==================== PAYMENT STATUS TESTS ====================

@pytest.mark.asyncio
async def test_check_payment_status_success(mock_stripe):
    """Test checking payment status"""
    status_info = await payment_service.check_payment_status("sub_test123")

    assert status_info is not None
    assert status_info["id"] == "sub_test123"
    assert status_info["status"] == "active"
    assert "current_period_end" in status_info


@pytest.mark.asyncio
async def test_check_payment_status_invalid_subscription(mock_stripe):
    """Test checking status for invalid subscription"""
    mock_stripe.Subscription.retrieve.side_effect = Exception("Subscription not found")

    status_info = await payment_service.check_payment_status("sub_invalid")

    assert status_info is None


# ==================== HELPER METHOD TESTS ====================

@pytest.mark.asyncio
async def test_get_or_create_customer_existing(mock_stripe):
    """Test getting existing Stripe customer"""
    customer = await payment_service._get_or_create_customer("existing@example.com")

    assert customer is not None
    assert customer.id == "cus_test123"


@pytest.mark.asyncio
async def test_get_or_create_customer_new(mock_stripe):
    """Test creating new Stripe customer"""
    mock_stripe.Customer.list.return_value = MagicMock(data=[])

    customer = await payment_service._get_or_create_customer("new@example.com")

    assert customer is not None
    assert customer.id == "cus_test123"


def test_get_price_id_valid_plans():
    """Test getting price IDs for valid plans"""
    basic_price = payment_service._get_price_id("basic")
    pro_price = payment_service._get_price_id("pro")
    business_price = payment_service._get_price_id("business")

    # These will be None in test environment, but the function should not error
    assert basic_price is None or isinstance(basic_price, str)
    assert pro_price is None or isinstance(pro_price, str)
    assert business_price is None or isinstance(business_price, str)


def test_get_price_id_invalid_plan():
    """Test getting price ID for invalid plan"""
    price_id = payment_service._get_price_id("invalid_plan")

    assert price_id is None


def test_get_plan_price_all_plans():
    """Test getting prices for all plans"""
    free_price = payment_service._get_plan_price("free")
    basic_price = payment_service._get_plan_price("basic")
    pro_price = payment_service._get_plan_price("pro")
    business_price = payment_service._get_plan_price("business")

    assert free_price == 0.0
    assert basic_price > 0
    assert pro_price > basic_price
    assert business_price > pro_price


# ==================== WEBHOOK HANDLER TESTS ====================

@pytest.mark.asyncio
async def test_stripe_webhook_subscription_created(
    client: AsyncClient,
    mock_stripe,
    mock_telegram_bot,
    mock_email_service
):
    """Test webhook handling for subscription.created event"""
    webhook_payload = b'{"type": "customer.subscription.created"}'

    with patch('app.routers.webhooks.auth_service.update_user_subscription', return_value=None):
        with patch('app.routers.webhooks.auth_service.get_user_by_email', return_value=None):
            response = await client.post(
                "/webhooks/stripe",
                content=webhook_payload,
                headers={"stripe-signature": "test_signature"}
            )

            assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_stripe_webhook_missing_signature(client: AsyncClient):
    """Test webhook with missing signature"""
    webhook_payload = b'{"type": "customer.subscription.created"}'

    response = await client.post(
        "/webhooks/stripe",
        content=webhook_payload
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_stripe_webhook_invalid_signature(client: AsyncClient, mock_stripe):
    """Test webhook with invalid signature"""
    webhook_payload = b'{"type": "customer.subscription.created"}'

    mock_stripe.Webhook.construct_event.side_effect = Exception("Invalid signature")

    response = await client.post(
        "/webhooks/stripe",
        content=webhook_payload,
        headers={"stripe-signature": "invalid_signature"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_stripe_webhook_subscription_deleted(
    client: AsyncClient,
    test_user_basic: User,
    mock_stripe,
    mock_telegram_bot,
    mock_email_service
):
    """Test webhook handling for subscription.deleted event"""
    webhook_event = {
        'type': 'customer.subscription.deleted',
        'data': {
            'object': {
                'customer': 'cus_test123'
            }
        }
    }

    with patch('app.routers.webhooks.stripe.Webhook.construct_event', return_value=webhook_event):
        with patch('app.routers.webhooks.auth_service.get_user_by_email', return_value=test_user_basic):
            with patch('app.routers.webhooks.auth_service.update_user_subscription', return_value=None):
                response = await client.post(
                    "/webhooks/stripe",
                    content=b'{}',
                    headers={"stripe-signature": "test_signature"}
                )

                assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_stripe_webhook_payment_succeeded(
    client: AsyncClient,
    test_user_basic: User,
    mock_stripe,
    mock_telegram_bot
):
    """Test webhook handling for invoice.payment_succeeded event"""
    webhook_event = {
        'type': 'invoice.payment_succeeded',
        'data': {
            'object': {
                'customer': 'cus_test123',
                'amount_paid': 500
            }
        }
    }

    with patch('app.routers.webhooks.stripe.Webhook.construct_event', return_value=webhook_event):
        with patch('app.routers.webhooks.auth_service.get_user_by_email', return_value=test_user_basic):
            with patch('app.routers.webhooks.auth_service.update_user_payment_info', return_value=None):
                with patch('app.services.invoice_service.invoice_service.generate_invoice', return_value=None):
                    response = await client.post(
                        "/webhooks/stripe",
                        content=b'{}',
                        headers={"stripe-signature": "test_signature"}
                    )

                    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_stripe_webhook_payment_failed(
    client: AsyncClient,
    test_user_basic: User,
    mock_stripe,
    mock_telegram_bot,
    mock_email_service
):
    """Test webhook handling for invoice.payment_failed event"""
    webhook_event = {
        'type': 'invoice.payment_failed',
        'data': {
            'object': {
                'customer': 'cus_test123',
                'amount_due': 500,
                'next_payment_attempt': int((datetime.utcnow() + timedelta(days=3)).timestamp())
            }
        }
    }

    with patch('app.routers.webhooks.stripe.Webhook.construct_event', return_value=webhook_event):
        with patch('app.routers.webhooks.auth_service.get_user_by_email', return_value=test_user_basic):
            with patch('app.routers.webhooks.auth_service.update_user_subscription', return_value=None):
                response = await client.post(
                    "/webhooks/stripe",
                    content=b'{}',
                    headers={"stripe-signature": "test_signature"}
                )

                assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_stripe_webhook_charge_refunded(
    client: AsyncClient,
    test_user_basic: User,
    mock_stripe,
    mock_telegram_bot
):
    """Test webhook handling for charge.refunded event"""
    webhook_event = {
        'type': 'charge.refunded',
        'data': {
            'object': {
                'customer': 'cus_test123',
                'amount_refunded': 500
            }
        }
    }

    with patch('app.routers.webhooks.stripe.Webhook.construct_event', return_value=webhook_event):
        with patch('app.routers.webhooks.auth_service.get_user_by_email', return_value=test_user_basic):
            with patch('app.routers.webhooks.auth_service.update_user_subscription', return_value=None):
                response = await client.post(
                    "/webhooks/stripe",
                    content=b'{}',
                    headers={"stripe-signature": "test_signature"}
                )

                assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_stripe_webhook_unhandled_event(client: AsyncClient, mock_stripe):
    """Test webhook with unhandled event type"""
    webhook_event = {
        'type': 'customer.updated',
        'data': {'object': {}}
    }

    with patch('app.routers.webhooks.stripe.Webhook.construct_event', return_value=webhook_event):
        response = await client.post(
            "/webhooks/stripe",
            content=b'{}',
            headers={"stripe-signature": "test_signature"}
        )

        # Should still return 200 OK even for unhandled events
        assert response.status_code == status.HTTP_200_OK
