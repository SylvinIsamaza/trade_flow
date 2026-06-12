"""
Email Service
Reusable email service with template support
"""
from typing import Optional, Dict, Any, List
from pathlib import Path
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Optional imports
try:
    import aiosmtplib
    SMTP_AVAILABLE = True
except ImportError:
    SMTP_AVAILABLE = False

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    JINJA_AVAILABLE = True
except ImportError:
    JINJA_AVAILABLE = False

from app.core.config import settings


class EmailService:
    """Reusable email service with Jinja2 template support."""
    
    def __init__(self, templates_dir: str = "app/templates/emails"):
        """
        Initialize email service.
        
        Args:
            templates_dir: Directory containing email templates
        """
        self.templates_dir = Path(templates_dir)
        self.env = None
        
        if self.templates_dir.exists() and JINJA_AVAILABLE:
            self.env = Environment(
                loader=FileSystemLoader(str(self.templates_dir)),
                autoescape=select_autoescape(['html', 'xml'])
            )
    
    def render_template(
        self, 
        template_name: str, 
        context: Dict[str, Any]
    ) -> str:
        """
        Render an email template with context data.
        
        Args:
            template_name: Name of template file (e.g., 'password_reset.html')
            context: Dictionary of data to pass to template
            
        Returns:
            Rendered template as string
        """
        if not self.env:
            # Return simple text if templates not configured
            return self._render_simple(template_name, context)
        
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            # Fallback to simple rendering
            return self._render_simple(template_name, context)
    
    def _render_simple(
        self, 
        template_name: str, 
        context: Dict[str, Any]
    ) -> str:
        """Simple text fallback when templates not available."""
        # Check if we have data to work with
        if isinstance(context.get('data'), dict):
            data = context['data']
            lines = []
            
            if template_name == 'password_reset':
                lines = [
                    f"Hello {data.get('name', 'User')},",
                    "",
                    "You requested a password reset.",
                    f"Click here to reset: {data.get('reset_url', '#')}",
                    "",
                    "This link expires in 1 hour.",
                ]
            elif template_name == 'welcome':
                lines = [
                    f"Welcome {data.get('name', 'User')}!",
                    "",
                    "Thank you for joining TradeZella.",
                    "Start tracking your trades today!",
                ]
            elif template_name == 'trade_imported':
                lines = [
                    f"Hello {data.get('name', 'User')},",
                    "",
                    f"Your trades have been imported successfully.",
                    f"Imported: {data.get('count', 0)} trades",
                ]
            elif template_name == 'contact':
                lines = [
                    "NEW CONTACT FORM SUBMISSION",
                    "",
                    f"From: {data.get('name', 'Unknown')} <{data.get('email', 'unknown@example.com')}>",
                    f"Subject: {data.get('subject', 'No subject')}",
                    "",
                    "Message:",
                    data.get('message', ''),
                ]
            elif template_name == 'contact_confirmation':
                lines = [
                    f"Thank you for contacting us, {data.get('name', 'User')}!",
                    "",
                    f"We've received your message about '{data.get('subject', 'your inquiry')}'.",
                    "Our team will review it and get back to you soon.",
                    "",
                    "Best regards,",
                    "The TradeFlow Team",
                ]
            else:
                # Generic fallback
                lines = [f"Hello {data.get('name', 'User')},"]
                for key, value in data.items():
                    lines.append(f"{key}: {value}")
            
            return "\n".join(lines)
        
        return f"Email: {template_name}"
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        template_name: Optional[str] = None,
        html_content: Optional[str] = None,
        text_content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        from_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            template_name: Name of template file (without extension)
            html_content: HTML content (if not using template)
            text_content: Plain text content (if not using template)
            context: Data to pass to template
            from_email: Sender email (defaults to config)
            
        Returns:
            Dict with success status and message
        """
        # Build email content
        if template_name and context:
            html_content = self.render_template(f"{template_name}.html", context)
            text_content = self.render_template(f"{template_name}.txt", context)
        
        if not html_content and not text_content:
            return {
                "success": False,
                "error": "No content provided"
            }
        
        # Determine from email
        from_email = from_email or settings.SMTP_FROM_EMAIL
        from_name = settings.SMTP_FROM_NAME or "TradeZella"
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{from_name} <{from_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg['Date'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
        
        # Attach content
        if text_content:
            msg.attach(MIMEText(text_content, 'plain'))
        if html_content:
            msg.attach(MIMEText(html_content, 'html'))
        
        # Send email
        try:
            if settings.SMTP_HOST and SMTP_AVAILABLE:
                await aiosmtplib.send(
                    msg,
                    hostname=settings.SMTP_HOST,
                    port=settings.SMTP_PORT or 587,
                    username=settings.SMTP_USER,
                    password=settings.SMTP_PASSWORD,
                    use_tls=settings.SMTP_USE_TLS,
                )
                return {
                    "success": True,
                    "message": f"Email sent to {to_email}"
                }
            else:
                # Development mode - just log
                print(f"[DEV EMAIL] To: {to_email}")
                print(f"[DEV EMAIL] Subject: {subject}")
                print(f"[DEV EMAIL] Content: {text_content or html_content}")
                return {
                    "success": True,
                    "message": f"[DEV] Email logged for {to_email}"
                }
                
        except ImportError:
            # aiosmtplib not available - log only
            print(f"[DEV EMAIL] To: {to_email}")
            print(f"[DEV EMAIL] Subject: {subject}")
            print(f"[DEV EMAIL] Content: {text_content or html_content}")
            return {
                "success": True,
                "message": f"[DEV] Email logged for {to_email} (smtp not available)"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_password_reset(
        self,
        to_email: str,
        name: str,
        reset_url: str,
    ) -> Dict[str, Any]:
        """Send password reset email."""
        return await self.send_email(
            to_email=to_email,
            subject="Reset your TradeZella password",
            template_name="password_reset",
            context={
                "data": {
                    "name": name,
                    "reset_url": reset_url,
                },
                "year": datetime.utcnow().year,
            }
        )
    
    async def send_welcome_email(
        self,
        to_email: str,
        name: str,
    ) -> Dict[str, Any]:
        """Send welcome email."""
        return await self.send_email(
            to_email=to_email,
            subject="Welcome to TradeFlow!",
            template_name="welcome",
            context={
                "data": {"name": name},
                "year": datetime.utcnow().year,
            }
        )
    
    async def send_trade_import_notification(
        self,
        to_email: str,
        name: str,
        account_name: str,
        trade_count: int,
    ) -> Dict[str, Any]:
        """Send trade import notification."""
        return await self.send_email(
            to_email=to_email,
            subject=f"Trades imported to {account_name}",
            template_name="trade_imported",
            context={
                "data": {
                    "name": name,
                    "account_name": account_name,
                    "count": trade_count,
                },
                "year": datetime.utcnow().year,
            }
        )
    
    async def send_batch_emails(
        self,
        emails: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send multiple emails.
        
        Args:
            emails: List of email configs with keys:
                   - to_email, subject, template_name, context
                   
        Returns:
            Dict with success count and errors
        """
        results = []
        success_count = 0
        errors = []
        
        for email_config in emails:
            result = await self.send_email(**email_config)
            if result.get("success"):
                success_count += 1
            else:
                errors.append({
                    "to": email_config.get("to_email"),
                    "error": result.get("error")
                })
        
        return {
            "total": len(emails),
            "success": success_count,
            "failed": len(errors),
            "errors": errors
        }


# Create singleton instance
email_service = EmailService()