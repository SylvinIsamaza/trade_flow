"""Contact form routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.contact import ContactRequest, ContactResponse
from app.services.email_service import EmailService
from app.core.config import settings
import logging

router = APIRouter(prefix="/api/contact", tags=["contact"])
logger = logging.getLogger(__name__)
email_service = EmailService()


@router.post("", response_model=ContactResponse)
async def send_contact_message(
    contact_data: ContactRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle contact form submission.
    
    Sends an email to the configured contact email with the form data.
    """
    try:
        # Prepare email context
        context = {
            "data": {
                "name": contact_data.name,
                "email": contact_data.email,
                "subject": contact_data.subject,
                "message": contact_data.message,
            }
        }
        
        # Send email to admin
        result = await email_service.send_email(
            to_email=settings.SMTP_FROM_EMAIL or "support@tradeflow.com",
            subject=f"New Contact Form: {contact_data.subject}",
            template_name="contact",
            context=context,
            from_email=settings.SMTP_FROM_EMAIL,
        )
        
        if not result.get("success"):
            logger.error(f"Failed to send contact email: {result.get('error')}")
            # Don't fail the request - still return success to user
            # but log the issue
        
        # Also send confirmation email to user
        confirmation_context = {
            "data": {
                "name": contact_data.name,
                "subject": contact_data.subject,
            }
        }
        
        await email_service.send_email(
            to_email=contact_data.email,
            subject="We received your message",
            template_name="contact_confirmation",
            context=confirmation_context,
            from_email=settings.SMTP_FROM_EMAIL,
        )
        
        logger.info(f"Contact form submitted by {contact_data.email}")
        
        return ContactResponse(
            success=True,
            message="Thank you for contacting us! We'll get back to you soon.",
            data={"email": contact_data.email},
        )
        
    except Exception as e:
        logger.error(f"Error processing contact form: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process contact form. Please try again later.",
        )
