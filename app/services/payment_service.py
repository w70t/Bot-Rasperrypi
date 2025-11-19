"""
Payment Service - Stripe Integration
Handles subscription creation, cancellation, updates, and refunds
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
import stripe
from app.config import get_settings
from app.database import Collections
from app.models.user import User

settings = get_settings()
logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentService:
    """
    Payment Service for handling Stripe operations
    """

    def __init__(self):
        self.stripe = stripe

    async def create_subscription(
        self,
        email: str,
        plan: str,
        payment_method: str
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Create a new subscription for a user

        Args:
            email: User's email address
            plan: Subscription plan (basic, pro, business)
            payment_method: Stripe payment method ID

        Returns:
            Tuple of (success, error_message, subscription_data)
        """
        try:
            # Get price ID for plan
            price_id = self._get_price_id(plan)
            if not price_id:
                return False, f"Invalid plan: {plan}", None

            # Create or get Stripe customer
            customer = await self._get_or_create_customer(email)
            if not customer:
                return False, "Failed to create customer", None

            # Attach payment method to customer
            try:
                self.stripe.PaymentMethod.attach(
                    payment_method,
                    customer=customer.id
                )

                # Set as default payment method
                self.stripe.Customer.modify(
                    customer.id,
                    invoice_settings={
                        'default_payment_method': payment_method
                    }
                )
            except stripe.error.StripeError as e:
                logger.error(f"Failed to attach payment method: {str(e)}")
                return False, f"Payment method error: {str(e)}", None

            # Create subscription
            subscription = self.stripe.Subscription.create(
                customer=customer.id,
                items=[{'price': price_id}],
                expand=['latest_invoice.payment_intent']
            )

            # Update user in MongoDB
            from app.services.auth_service import auth_service
            await auth_service.update_user_subscription(
                email=email,
                plan=plan,
                stripe_customer_id=customer.id,
                stripe_subscription_id=subscription.id,
                status='active'
            )

            # Send notification
            from app.telegram_bot import telegram_bot
            price = self._get_plan_price(plan)
            await telegram_bot.notify_new_subscriber(email, plan, price)

            # Send welcome email
            from app.utils.email_service import email_service
            user = await auth_service.get_user_by_email(email)
            if user:
                await email_service.send_welcome_email(user.email, user.api_key)

            subscription_data = {
                'subscription_id': subscription.id,
                'customer_id': customer.id,
                'status': subscription.status,
                'current_period_end': subscription.current_period_end
            }

            logger.info(f"✓ Subscription created: {email} - {plan}")
            return True, None, subscription_data

        except stripe.error.CardError as e:
            logger.error(f"Card error: {str(e)}")
            return False, f"Card error: {e.user_message}", None

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {str(e)}")
            return False, f"Payment error: {str(e)}", None

        except Exception as e:
            logger.error(f"Error creating subscription: {str(e)}", exc_info=True)
            return False, f"System error: {str(e)}", None

    async def cancel_subscription(
        self,
        user_email: str,
        reason: str = "User requested"
    ) -> Tuple[bool, Optional[str]]:
        """
        Cancel a user's subscription

        Args:
            user_email: User's email
            reason: Cancellation reason

        Returns:
            Tuple of (success, error_message)
        """
        try:
            from app.services.auth_service import auth_service

            # Get user
            user = await auth_service.get_user_by_email(user_email)
            if not user:
                return False, "User not found"

            if not user.stripe_subscription_id:
                return False, "No active subscription"

            # Cancel in Stripe
            subscription = self.stripe.Subscription.modify(
                user.stripe_subscription_id,
                cancel_at_period_end=True,
                metadata={'cancellation_reason': reason}
            )

            # Update MongoDB
            await auth_service.update_user_subscription(
                email=user_email,
                status='canceling',
                cancellation_reason=reason,
                cancellation_date=datetime.utcnow()
            )

            # Send notification
            from app.telegram_bot import telegram_bot
            await telegram_bot.send_notification(
                f"🔴 اشتراك ملغي\n\n"
                f"📧 Email: {user_email}\n"
                f"📦 Plan: {user.plan}\n"
                f"📝 Reason: {reason}\n"
                f"🗓️ Ends: {datetime.fromtimestamp(subscription.current_period_end).strftime('%Y-%m-%d')}"
            )

            # Send cancellation email
            from app.utils.email_service import email_service
            await email_service.send_subscription_ending(
                user_email,
                days_left=(datetime.fromtimestamp(subscription.current_period_end) - datetime.utcnow()).days
            )

            logger.info(f"✓ Subscription cancelled: {user_email} - {reason}")
            return True, None

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error cancelling subscription: {str(e)}")
            return False, f"Payment error: {str(e)}"

        except Exception as e:
            logger.error(f"Error cancelling subscription: {str(e)}", exc_info=True)
            return False, f"System error: {str(e)}"

    async def update_subscription(
        self,
        user_email: str,
        new_plan: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Update a user's subscription plan

        Args:
            user_email: User's email
            new_plan: New subscription plan

        Returns:
            Tuple of (success, error_message)
        """
        try:
            from app.services.auth_service import auth_service

            # Get user
            user = await auth_service.get_user_by_email(user_email)
            if not user:
                return False, "User not found"

            if not user.stripe_subscription_id:
                return False, "No active subscription"

            # Get new price ID
            new_price_id = self._get_price_id(new_plan)
            if not new_price_id:
                return False, f"Invalid plan: {new_plan}"

            # Get subscription
            subscription = self.stripe.Subscription.retrieve(user.stripe_subscription_id)

            # Update subscription (with proration)
            updated_subscription = self.stripe.Subscription.modify(
                user.stripe_subscription_id,
                items=[{
                    'id': subscription['items']['data'][0].id,
                    'price': new_price_id,
                }],
                proration_behavior='create_prorations'
            )

            # Update MongoDB
            await auth_service.update_user_plan(user_email, new_plan)

            # Send notification
            from app.telegram_bot import telegram_bot
            await telegram_bot.send_notification(
                f"⬆️ ترقية اشتراك\n\n"
                f"📧 Email: {user_email}\n"
                f"📦 From: {user.plan} → To: {new_plan}\n"
                f"💰 New price: ${self._get_plan_price(new_plan)}/month"
            )

            # Send upgrade email
            from app.utils.email_service import email_service
            await email_service.send_upgrade_confirmation(user_email, new_plan)

            logger.info(f"✓ Subscription updated: {user_email} - {user.plan} → {new_plan}")
            return True, None

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error updating subscription: {str(e)}")
            return False, f"Payment error: {str(e)}"

        except Exception as e:
            logger.error(f"Error updating subscription: {str(e)}", exc_info=True)
            return False, f"System error: {str(e)}"

    async def process_refund(
        self,
        user_email: str,
        amount: Optional[float] = None,
        reason: str = "requested_by_customer"
    ) -> Tuple[bool, Optional[str]]:
        """
        Process a refund for a user

        Args:
            user_email: User's email
            amount: Refund amount (None = full refund)
            reason: Refund reason

        Returns:
            Tuple of (success, error_message)
        """
        try:
            from app.services.auth_service import auth_service

            # Get user
            user = await auth_service.get_user_by_email(user_email)
            if not user:
                return False, "User not found"

            if not user.stripe_customer_id:
                return False, "No payment history"

            # Check eligibility (< 7 days for full refund, < 14 days for partial)
            days_since_subscription = (datetime.utcnow() - user.created_at).days

            if days_since_subscription > 14:
                return False, "Refund period expired (14 days)"

            # Get last payment intent
            charges = self.stripe.Charge.list(
                customer=user.stripe_customer_id,
                limit=1
            )

            if not charges.data:
                return False, "No charges found"

            last_charge = charges.data[0]

            # Calculate refund amount
            if amount is None:
                if days_since_subscription <= 7:
                    # Full refund within 7 days
                    refund_amount = last_charge.amount
                else:
                    # Partial refund (50%) within 14 days
                    refund_amount = int(last_charge.amount * 0.5)
            else:
                refund_amount = int(amount * 100)  # Convert to cents

            # Create refund
            refund = self.stripe.Refund.create(
                charge=last_charge.id,
                amount=refund_amount,
                reason=reason
            )

            # Update MongoDB
            await auth_service.update_user_subscription(
                email=user_email,
                status='refunded',
                refund_amount=refund_amount / 100,
                refund_date=datetime.utcnow()
            )

            # Send notification
            from app.telegram_bot import telegram_bot
            await telegram_bot.send_notification(
                f"💸 استرداد أموال\n\n"
                f"📧 Email: {user_email}\n"
                f"💰 Amount: ${refund_amount/100:.2f}\n"
                f"📝 Reason: {reason}"
            )

            # Send refund confirmation email
            from app.utils.email_service import email_service
            await email_service.send_refund_confirmation(user_email, refund_amount / 100)

            logger.info(f"✓ Refund processed: {user_email} - ${refund_amount/100:.2f}")
            return True, None

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error processing refund: {str(e)}")
            return False, f"Payment error: {str(e)}"

        except Exception as e:
            logger.error(f"Error processing refund: {str(e)}", exc_info=True)
            return False, f"System error: {str(e)}"

    async def check_payment_status(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """
        Check payment status for a subscription

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            Dictionary with subscription status information
        """
        try:
            subscription = self.stripe.Subscription.retrieve(subscription_id)

            return {
                'id': subscription.id,
                'status': subscription.status,
                'current_period_start': subscription.current_period_start,
                'current_period_end': subscription.current_period_end,
                'cancel_at_period_end': subscription.cancel_at_period_end,
                'canceled_at': subscription.canceled_at,
            }

        except stripe.error.StripeError as e:
            logger.error(f"Error checking payment status: {str(e)}")
            return None

        except Exception as e:
            logger.error(f"Error checking payment status: {str(e)}", exc_info=True)
            return None

    # ==================== HELPER METHODS ====================

    async def _get_or_create_customer(self, email: str) -> Optional[stripe.Customer]:
        """
        Get existing Stripe customer or create new one

        Args:
            email: Customer email

        Returns:
            Stripe Customer object or None
        """
        try:
            # Search for existing customer
            customers = self.stripe.Customer.list(email=email, limit=1)

            if customers.data:
                return customers.data[0]

            # Create new customer
            customer = self.stripe.Customer.create(
                email=email,
                metadata={'source': 'tiktok_api'}
            )

            return customer

        except stripe.error.StripeError as e:
            logger.error(f"Error getting/creating customer: {str(e)}")
            return None

    def _get_price_id(self, plan: str) -> Optional[str]:
        """
        Get Stripe price ID for a plan

        Args:
            plan: Plan name (basic, pro, business)

        Returns:
            Stripe price ID or None
        """
        price_mapping = {
            'basic': settings.STRIPE_PRICE_BASIC,
            'pro': settings.STRIPE_PRICE_PRO,
            'business': settings.STRIPE_PRICE_BUSINESS
        }

        return price_mapping.get(plan.lower())

    def _get_plan_price(self, plan: str) -> float:
        """
        Get price for a plan

        Args:
            plan: Plan name

        Returns:
            Price in USD
        """
        price_mapping = {
            'free': settings.PRICE_FREE,
            'basic': settings.PRICE_BASIC,
            'pro': settings.PRICE_PRO,
            'business': settings.PRICE_BUSINESS
        }

        return price_mapping.get(plan.lower(), 0.0)


# Singleton instance
payment_service = PaymentService()
