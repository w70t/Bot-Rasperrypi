"""
Webhooks Router - Stripe Webhook Handler
Handles Stripe webhook events for subscription management
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, status
import stripe
from app.config import get_settings
from app.services.auth_service import auth_service
from app.services.payment_service import payment_service
from app.telegram_bot import telegram_bot

settings = get_settings()
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events

    Supported events:
    - customer.subscription.created
    - customer.subscription.deleted
    - customer.subscription.updated
    - invoice.payment_succeeded
    - invoice.payment_failed
    - charge.refunded
    """
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    if not sig_header:
        logger.error("Missing stripe-signature header")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header"
        )

    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET
        )

    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload"
        )

    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )

    # Get event type and data
    event_type = event['type']
    data_object = event['data']['object']

    logger.info(f"Received Stripe webhook: {event_type}")

    # Handle events
    try:
        if event_type == 'customer.subscription.created':
            await handle_subscription_created(data_object)

        elif event_type == 'customer.subscription.deleted':
            await handle_subscription_deleted(data_object)

        elif event_type == 'customer.subscription.updated':
            await handle_subscription_updated(data_object)

        elif event_type == 'invoice.payment_succeeded':
            await handle_payment_succeeded(data_object)

        elif event_type == 'invoice.payment_failed':
            await handle_payment_failed(data_object)

        elif event_type == 'charge.refunded':
            await handle_charge_refunded(data_object)

        else:
            logger.info(f"Unhandled event type: {event_type}")

    except Exception as e:
        logger.error(f"Error handling webhook {event_type}: {str(e)}", exc_info=True)

        # Send error notification
        await telegram_bot.notify_error(
            error_type=f"Webhook Error ({event_type})",
            error_msg=str(e)
        )

        # Still return 200 to acknowledge receipt
        # (Stripe will retry failed webhooks automatically)

    return {"success": True}


# ==================== EVENT HANDLERS ====================


async def handle_subscription_created(subscription):
    """
    Handle customer.subscription.created event

    Args:
        subscription: Stripe subscription object
    """
    try:
        customer_id = subscription['customer']
        subscription_id = subscription['id']
        status_str = subscription['status']

        # Get customer email
        customer = stripe.Customer.retrieve(customer_id)
        email = customer['email']

        # Determine plan from price ID
        price_id = subscription['items']['data'][0]['price']['id']
        plan = _get_plan_from_price_id(price_id)

        if not plan:
            logger.error(f"Unknown price ID: {price_id}")
            return

        # Update user in database
        await auth_service.update_user_subscription(
            email=email,
            plan=plan,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            status='active'
        )

        # Send notification
        price = payment_service._get_plan_price(plan)
        await telegram_bot.send_notification(
            f"✅ اشتراك مفعّل\n\n"
            f"📧 Email: {email}\n"
            f"📦 Plan: {plan.upper()}\n"
            f"💰 ${price}/month\n"
            f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

        logger.info(f"✓ Subscription created: {email} - {plan}")

    except Exception as e:
        logger.error(f"Error in handle_subscription_created: {str(e)}", exc_info=True)
        raise


async def handle_subscription_deleted(subscription):
    """
    Handle customer.subscription.deleted event

    Args:
        subscription: Stripe subscription object
    """
    try:
        customer_id = subscription['customer']

        # Get customer email
        customer = stripe.Customer.retrieve(customer_id)
        email = customer['email']

        # Get user
        user = await auth_service.get_user_by_email(email)
        if not user:
            logger.warning(f"User not found for deleted subscription: {email}")
            return

        # Downgrade to free plan
        await auth_service.update_user_subscription(
            email=email,
            plan='free',
            status='inactive',
            stripe_subscription_id=None
        )

        # Send notification
        await telegram_bot.send_notification(
            f"❌ اشتراك منتهي\n\n"
            f"📧 Email: {email}\n"
            f"📦 Was: {user.plan.upper()}\n"
            f"➡️ Now: FREE\n"
            f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

        # Send email to user
        from app.utils.email_service import email_service
        await email_service.send_subscription_ended(email)

        logger.info(f"✓ Subscription deleted: {email}")

    except Exception as e:
        logger.error(f"Error in handle_subscription_deleted: {str(e)}", exc_info=True)
        raise


async def handle_subscription_updated(subscription):
    """
    Handle customer.subscription.updated event

    Args:
        subscription: Stripe subscription object
    """
    try:
        customer_id = subscription['customer']
        status_str = subscription['status']
        cancel_at_period_end = subscription['cancel_at_period_end']

        # Get customer email
        customer = stripe.Customer.retrieve(customer_id)
        email = customer['email']

        # Determine plan from price ID
        price_id = subscription['items']['data'][0]['price']['id']
        plan = _get_plan_from_price_id(price_id)

        if not plan:
            logger.error(f"Unknown price ID: {price_id}")
            return

        # Update user
        update_status = 'active' if status_str == 'active' and not cancel_at_period_end else 'canceling'

        await auth_service.update_user_subscription(
            email=email,
            plan=plan,
            status=update_status
        )

        # Send notification
        await telegram_bot.send_notification(
            f"🔄 اشتراك محدث\n\n"
            f"📧 Email: {email}\n"
            f"📦 Plan: {plan.upper()}\n"
            f"📊 Status: {update_status}\n"
            f"🔚 Cancel at end: {'Yes' if cancel_at_period_end else 'No'}\n"
            f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

        logger.info(f"✓ Subscription updated: {email} - {plan} - {update_status}")

    except Exception as e:
        logger.error(f"Error in handle_subscription_updated: {str(e)}", exc_info=True)
        raise


async def handle_payment_succeeded(invoice):
    """
    Handle invoice.payment_succeeded event

    Args:
        invoice: Stripe invoice object
    """
    try:
        customer_id = invoice['customer']
        amount_paid = invoice['amount_paid'] / 100  # Convert from cents

        # Get customer email
        customer = stripe.Customer.retrieve(customer_id)
        email = customer['email']

        # Get user
        user = await auth_service.get_user_by_email(email)
        if not user:
            logger.warning(f"User not found for payment: {email}")
            return

        # Update last payment date
        await auth_service.update_user_payment_info(
            email=email,
            last_payment_date=datetime.utcnow(),
            last_payment_amount=amount_paid
        )

        # Generate and send invoice
        from app.services.invoice_service import invoice_service
        invoice_pdf = await invoice_service.generate_invoice(
            user_email=email,
            amount=amount_paid,
            plan=user.plan,
            period=invoice.get('period_end', datetime.utcnow().strftime('%Y-%m-%d'))
        )

        if invoice_pdf:
            await invoice_service.send_invoice_email(email, invoice_pdf)

        # Send notification
        await telegram_bot.send_notification(
            f"💳 دفع ناجح\n\n"
            f"📧 Email: {email}\n"
            f"💰 Amount: ${amount_paid:.2f}\n"
            f"📦 Plan: {user.plan.upper()}\n"
            f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

        logger.info(f"✓ Payment succeeded: {email} - ${amount_paid}")

    except Exception as e:
        logger.error(f"Error in handle_payment_succeeded: {str(e)}", exc_info=True)
        raise


async def handle_payment_failed(invoice):
    """
    Handle invoice.payment_failed event

    Args:
        invoice: Stripe invoice object
    """
    try:
        customer_id = invoice['customer']
        amount_due = invoice['amount_due'] / 100

        # Get customer email
        customer = stripe.Customer.retrieve(customer_id)
        email = customer['email']

        # Get next retry date
        next_payment_attempt = invoice.get('next_payment_attempt')
        retry_date = datetime.fromtimestamp(next_payment_attempt).strftime('%Y-%m-%d') if next_payment_attempt else 'Unknown'

        # Update user status
        await auth_service.update_user_subscription(
            email=email,
            status='payment_failed'
        )

        # Send notification
        await telegram_bot.send_notification(
            f"⚠️ فشل الدفع\n\n"
            f"📧 Email: {email}\n"
            f"💰 Amount: ${amount_due:.2f}\n"
            f"🔄 Retry: {retry_date}\n"
            f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

        # Send email to user
        from app.utils.email_service import email_service
        await email_service.send_payment_failed(email, retry_date)

        logger.warning(f"⚠️ Payment failed: {email} - ${amount_due}")

    except Exception as e:
        logger.error(f"Error in handle_payment_failed: {str(e)}", exc_info=True)
        raise


async def handle_charge_refunded(charge):
    """
    Handle charge.refunded event

    Args:
        charge: Stripe charge object
    """
    try:
        customer_id = charge.get('customer')
        if not customer_id:
            logger.warning("Refund charge has no customer")
            return

        amount_refunded = charge['amount_refunded'] / 100

        # Get customer email
        customer = stripe.Customer.retrieve(customer_id)
        email = customer['email']

        # Update user
        await auth_service.update_user_subscription(
            email=email,
            status='refunded',
            refund_amount=amount_refunded,
            refund_date=datetime.utcnow()
        )

        # Send notification
        await telegram_bot.send_notification(
            f"💸 استرداد مؤكد\n\n"
            f"📧 Email: {email}\n"
            f"💰 Amount: ${amount_refunded:.2f}\n"
            f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

        logger.info(f"✓ Refund processed: {email} - ${amount_refunded}")

    except Exception as e:
        logger.error(f"Error in handle_charge_refunded: {str(e)}", exc_info=True)
        raise


# ==================== HELPER FUNCTIONS ====================


def _get_plan_from_price_id(price_id: str) -> str:
    """
    Get plan name from Stripe price ID

    Args:
        price_id: Stripe price ID

    Returns:
        Plan name (basic, pro, business) or empty string
    """
    price_mapping = {
        settings.STRIPE_PRICE_BASIC: 'basic',
        settings.STRIPE_PRICE_PRO: 'pro',
        settings.STRIPE_PRICE_BUSINESS: 'business'
    }

    return price_mapping.get(price_id, '')
