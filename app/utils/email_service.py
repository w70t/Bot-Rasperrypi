"""
Email Service - SMTP Email Sending
Handles all email communications with users
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional
import aiosmtplib
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class EmailService:
    """
    Email Service for sending transactional emails
    """

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = False
    ) -> bool:
        """
        Send email

        Args:
            to_email: Recipient email
            subject: Email subject
            body: Email body
            html: Whether body is HTML

        Returns:
            True if sent successfully
        """
        try:
            message = MIMEMultipart('alternative')
            message['From'] = f"{self.from_name} <{self.from_email}>"
            message['To'] = to_email
            message['Subject'] = subject

            # Attach body
            if html:
                part = MIMEText(body, 'html')
            else:
                part = MIMEText(body, 'plain')

            message.attach(part)

            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_username,
                password=self.smtp_password,
                use_tls=True
            )

            logger.info(f"✓ Email sent to: {to_email}")
            return True

        except Exception as e:
            logger.error(f"Error sending email: {str(e)}", exc_info=True)
            return False

    async def send_email_with_attachment(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachment_data: bytes,
        attachment_name: str
    ) -> bool:
        """
        Send email with attachment

        Args:
            to_email: Recipient email
            subject: Email subject
            body: Email body
            attachment_data: Attachment bytes
            attachment_name: Attachment filename

        Returns:
            True if sent successfully
        """
        try:
            message = MIMEMultipart()
            message['From'] = f"{self.from_name} <{self.from_email}>"
            message['To'] = to_email
            message['Subject'] = subject

            # Attach body
            message.attach(MIMEText(body, 'plain'))

            # Attach file
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment_data)
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {attachment_name}'
            )
            message.attach(part)

            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_username,
                password=self.smtp_password,
                use_tls=True
            )

            logger.info(f"✓ Email with attachment sent to: {to_email}")
            return True

        except Exception as e:
            logger.error(f"Error sending email with attachment: {str(e)}", exc_info=True)
            return False

    # ==================== TEMPLATE EMAILS ====================

    async def send_welcome_email(self, user_email: str, api_key: str):
        """Send welcome email to new user"""
        subject = f"Welcome to {settings.APP_NAME}!"
        body = f"""
Welcome to {settings.APP_NAME}!

Thank you for signing up. Here are your account details:

Email: {user_email}
API Key: {api_key}

Getting Started:
1. Read our documentation: https://docs.yourdomain.com
2. Test your first request
3. Check your usage dashboard

Need help? Reply to this email or contact support@yourdomain.com

Best regards,
The {settings.APP_NAME} Team
        """

        await self.send_email(user_email, subject, body)

    async def send_upgrade_reminder(self, user_email: str, usage_percent: int):
        """Send upgrade reminder when user reaches 90% usage"""
        subject = "You're running out of API requests"
        body = f"""
Hi there,

You've used {usage_percent}% of your monthly API requests.

To avoid service interruptions, consider upgrading your plan:

• Pro Plan: 10,000 requests/month ($20)
• Business Plan: 100,000 requests/month ($100)

Upgrade now: https://yourdomain.com/upgrade

Questions? Contact us at support@yourdomain.com

Best regards,
The {settings.APP_NAME} Team
        """

        await self.send_email(user_email, subject, body)

    async def send_payment_failed(self, user_email: str, retry_date: str):
        """Send notification when payment fails"""
        subject = "Payment Failed - Action Required"
        body = f"""
Hi there,

We were unable to process your payment for {settings.APP_NAME}.

Next retry: {retry_date}

Please update your payment method to avoid service interruption:
https://yourdomain.com/billing

Need help? Contact support@yourdomain.com

Best regards,
The {settings.APP_NAME} Team
        """

        await self.send_email(user_email, subject, body)

    async def send_subscription_ending(self, user_email: str, days_left: int):
        """Send notification before subscription ends"""
        subject = f"Your subscription ends in {days_left} days"
        body = f"""
Hi there,

Your {settings.APP_NAME} subscription will end in {days_left} days.

To continue enjoying our service, please renew:
https://yourdomain.com/renew

Questions? Contact support@yourdomain.com

Best regards,
The {settings.APP_NAME} Team
        """

        await self.send_email(user_email, subject, body)

    async def send_subscription_ended(self, user_email: str):
        """Send notification when subscription ends"""
        subject = "Your subscription has ended"
        body = f"""
Hi there,

Your {settings.APP_NAME} subscription has ended.

We're sorry to see you go! You've been downgraded to the Free plan.

Want to come back? Reactivate anytime:
https://yourdomain.com/plans

We'd love to hear why you left:
https://yourdomain.com/feedback

Best regards,
The {settings.APP_NAME} Team
        """

        await self.send_email(user_email, subject, body)

    async def send_refund_confirmation(self, user_email: str, amount: float):
        """Send refund confirmation"""
        subject = "Refund Processed"
        body = f"""
Hi there,

Your refund of ${amount:.2f} has been processed.

It should appear in your account within 5-10 business days.

Questions? Contact support@yourdomain.com

Best regards,
The {settings.APP_NAME} Team
        """

        await self.send_email(user_email, subject, body)

    async def send_upgrade_confirmation(self, user_email: str, new_plan: str):
        """Send upgrade confirmation"""
        subject = f"Upgraded to {new_plan.upper()} Plan"
        body = f"""
Hi there,

Congratulations! Your account has been upgraded to the {new_plan.upper()} plan.

You now have access to:
• Increased request limits
• Higher rate limits
• Premium features

View your new limits: https://yourdomain.com/dashboard

Thank you for upgrading!

Best regards,
The {settings.APP_NAME} Team
        """

        await self.send_email(user_email, subject, body)


# Singleton instance
email_service = EmailService()
