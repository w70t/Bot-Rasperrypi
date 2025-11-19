"""
Invoice Service - PDF Invoice Generation
Generates and sends invoices for subscription payments
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class InvoiceService:
    """
    Invoice Service for generating PDF invoices
    """

    def __init__(self):
        self.invoices_dir = Path('invoices')
        self.invoices_dir.mkdir(parents=True, exist_ok=True)

    async def generate_invoice(
        self,
        user_email: str,
        amount: float,
        plan: str,
        period: str,
        invoice_number: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Generate PDF invoice

        Args:
            user_email: User's email
            amount: Invoice amount in USD
            plan: Subscription plan
            period: Billing period
            invoice_number: Invoice number (auto-generated if None)

        Returns:
            PDF bytes or None if failed
        """
        try:
            from app.database import Collections

            # Generate invoice number if not provided
            if not invoice_number:
                timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                invoice_number = f"INV-{timestamp}"

            invoice_date = datetime.utcnow()

            # Create PDF in memory
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()

            # Header
            header = Paragraph(
                f"<b>INVOICE #{invoice_number}</b>",
                styles['Title']
            )
            story.append(header)
            story.append(Spacer(1, 0.3*inch))

            # Company Info
            company_info = Paragraph(
                f"""
                <b>{settings.APP_NAME}</b><br/>
                Your Company Address<br/>
                City, State, ZIP<br/>
                Email: support@yourdomain.com
                """,
                styles['Normal']
            )
            story.append(company_info)
            story.append(Spacer(1, 0.3*inch))

            # Invoice Date
            date_info = Paragraph(
                f"<b>Date:</b> {invoice_date.strftime('%B %d, %Y')}",
                styles['Normal']
            )
            story.append(date_info)
            story.append(Spacer(1, 0.2*inch))

            # Bill To
            bill_to = Paragraph(
                f"""
                <b>Bill To:</b><br/>
                {user_email}
                """,
                styles['Normal']
            )
            story.append(bill_to)
            story.append(Spacer(1, 0.3*inch))

            # Invoice Details Table
            data = [
                ['Description', 'Period', 'Amount'],
                [f'{plan.upper()} Plan Subscription', period, f'${amount:.2f}'],
                ['', 'Subtotal:', f'${amount:.2f}'],
                ['', 'Tax:', '$0.00'],
                ['', '<b>Total:</b>', f'<b>${amount:.2f}</b>']
            ]

            table = Table(data, colWidths=[3*inch, 2*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -3), colors.beige),
                ('GRID', (0, 0), (-1, -3), 1, colors.black),
                ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
            ]))

            story.append(table)
            story.append(Spacer(1, 0.5*inch))

            # Payment Info
            payment_info = Paragraph(
                """
                <b>Payment Method:</b> Credit Card (via Stripe)<br/>
                <b>Status:</b> PAID
                """,
                styles['Normal']
            )
            story.append(payment_info)
            story.append(Spacer(1, 0.3*inch))

            # Footer
            footer = Paragraph(
                """
                <i>Thank you for your business!</i><br/>
                Questions? Contact us at support@yourdomain.com
                """,
                styles['Normal']
            )
            story.append(footer)

            # Build PDF
            doc.build(story)

            # Get PDF bytes
            pdf_bytes = buffer.getvalue()
            buffer.close()

            # Save to file (optional)
            invoice_file = self.invoices_dir / f"{invoice_number}.pdf"
            with open(invoice_file, 'wb') as f:
                f.write(pdf_bytes)

            # Store invoice metadata in database
            invoice_metadata = {
                "invoice_number": invoice_number,
                "user_email": user_email,
                "amount": amount,
                "plan": plan,
                "period": period,
                "invoice_date": invoice_date,
                "status": "paid",
                "created_at": invoice_date
            }

            await Collections.invoices().insert_one(invoice_metadata)

            logger.info(f"✓ Invoice generated and stored: {invoice_number}")
            return pdf_bytes

        except Exception as e:
            logger.error(f"Error generating invoice: {str(e)}", exc_info=True)
            return None

    async def send_invoice_email(self, user_email: str, invoice_pdf: bytes):
        """
        Send invoice via email

        Args:
            user_email: Recipient email
            invoice_pdf: PDF bytes
        """
        try:
            from app.utils.email_service import email_service

            await email_service.send_email_with_attachment(
                to_email=user_email,
                subject="Your Invoice - TikTok API",
                body="Thank you for your payment. Please find your invoice attached.",
                attachment_data=invoice_pdf,
                attachment_name="invoice.pdf"
            )

            logger.info(f"✓ Invoice emailed to: {user_email}")

        except Exception as e:
            logger.error(f"Error sending invoice email: {str(e)}", exc_info=True)

    async def get_user_invoices(self, user_email: str) -> list:
        """
        Get list of invoices for a user

        Args:
            user_email: User's email

        Returns:
            List of invoice metadata dictionaries
        """
        try:
            from app.database import Collections

            # Query invoices collection filtered by user_email
            cursor = Collections.invoices().find(
                {"user_email": user_email},
                {
                    "invoice_number": 1,
                    "amount": 1,
                    "plan": 1,
                    "period": 1,
                    "invoice_date": 1,
                    "status": 1,
                    "_id": 0
                }
            ).sort("invoice_date", -1)  # Most recent first

            invoices = await cursor.to_list(length=None)

            logger.info(f"Retrieved {len(invoices)} invoices for {user_email}")
            return invoices

        except Exception as e:
            logger.error(f"Error getting user invoices: {str(e)}")
            return []


# Singleton instance
invoice_service = InvoiceService()
