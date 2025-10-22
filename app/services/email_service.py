"""Email service for sending transactional emails with templates."""

import logging
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service for sending transactional emails using ZeptoMail API.

    Supports:
    - OTP verification emails
    - Welcome emails
    - Password reset emails
    - HTML template rendering
    """

    def __init__(self):
        self.api_url = settings.ZEPTO_API_URL
        self.send_token = settings.ZEPTO_SEND_TOKEN
        self.from_email = settings.ZEPTO_FROM_EMAIL
        self.from_name = settings.ZEPTO_FROM_NAME

        # Email templates directory (backend/email_templates/)
        self.templates_dir = Path(__file__).parent.parent.parent / "email_templates"

        # Check if ZeptoMail is configured
        self.is_configured = bool(self.send_token)

        if not self.is_configured:
            logger.warning(
                'ZeptoMail not configured - emails will be logged only',
                extra={'api_url': self.api_url},
            )

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        to_name: str | None = None,
    ) -> bool:
        """
        Send an email using ZeptoMail API.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_body: HTML email content
            to_name: Recipient name (optional)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.info(
                'Email sending skipped (ZeptoMail not configured)',
                extra={
                    'to': to_email,
                    'subject': subject,
                    'html_preview': html_body[:100] + '...' if len(html_body) > 100 else html_body,
                },
            )
            return True  # Return success to not block development

        try:
            # Build headers
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "authorization": f"Zoho-enczapikey {self.send_token}",
            }

            # Build payload matching ZeptoMail format
            to_data = {"email_address": {"address": to_email}}
            if to_name:
                to_data["email_address"]["name"] = to_name

            payload = {
                "from": {"address": self.from_email, "name": self.from_name},
                "to": [to_data],
                "subject": subject,
                "htmlbody": html_body,
            }

            # Send email via API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    logger.info(
                        'Email sent successfully via ZeptoMail API',
                        extra={'to': to_email, 'subject': subject},
                    )
                    return True
                else:
                    logger.error(
                        'ZeptoMail API returned non-200 status',
                        extra={
                            'to': to_email,
                            'subject': subject,
                            'status_code': response.status_code,
                            'response': response.text[:500],  # Limit response length
                        },
                    )
                    # Note: Email might still be delivered even with non-200 response
                    # ZeptoMail can accept email but return errors for billing/quota warnings
                    return False

        except Exception as e:
            logger.error(
                'Failed to send email via ZeptoMail API',
                extra={'to': to_email, 'subject': subject, 'error': str(e)},
                exc_info=True,
            )
            return False

    async def send_otp_email(self, email: str, otp: str, user_name: str | None = None) -> bool:
        """
        Send OTP verification email.

        Args:
            email: User's email address
            otp: 6-digit OTP code
            user_name: User's name (optional, for personalization)

        Returns:
            True if email sent successfully
        """
        try:
            # Load OTP template
            template_path = self.templates_dir / "otp_verification.html"

            if not template_path.exists():
                logger.error('OTP email template not found', extra={'path': str(template_path)})
                return False

            with open(template_path, "r", encoding="utf-8") as f:
                html_template = f.read()

            # Replace template variables
            html_body = html_template.replace("{{OTP_CODE}}", otp)
            html_body = html_body.replace("{{USER_EMAIL}}", email)

            # Add user name if provided
            if user_name:
                html_body = html_body.replace("{{USER_NAME}}", user_name)

            # Create verification deep link (for one-click verification)
            verification_link = f"https://api.jiran.app/api/v1/auth/verify-email?code={otp}&email={email}"
            html_body = html_body.replace("{{VERIFICATION_LINK}}", verification_link)

            # Send email
            return await self.send_email(
                to_email=email,
                subject="Verify Your Jiran Account - OTP Inside",
                html_body=html_body,
                to_name=user_name,
            )

        except Exception as e:
            logger.error('Failed to send OTP email', extra={'email': email, 'error': str(e)}, exc_info=True)
            return False

    async def send_welcome_email(self, email: str, name: str) -> bool:
        """
        Send welcome email to new users.

        Args:
            email: User's email address
            name: User's full name

        Returns:
            True if email sent successfully
        """
        try:
            # Load welcome template
            template_path = self.templates_dir / "welcome.html"

            if not template_path.exists():
                logger.error('Welcome email template not found', extra={'path': str(template_path)})
                return False

            with open(template_path, "r", encoding="utf-8") as f:
                html_template = f.read()

            # Replace template variables
            html_body = html_template.replace("{{USER_NAME}}", name)
            html_body = html_body.replace("{{USER_EMAIL}}", email)
            html_body = html_body.replace("{{APP_LINK}}", "https://jiran.app")
            html_body = html_body.replace("{{BROWSE_LINK}}", "https://jiran.app/browse")
            html_body = html_body.replace("{{IOS_APP_LINK}}", "https://apps.apple.com/app/jiran")
            html_body = html_body.replace("{{ANDROID_APP_LINK}}", "https://play.google.com/store/apps/jiran")
            html_body = html_body.replace("{{SUPPORT_EMAIL}}", "support@jiran.app")
            html_body = html_body.replace("{{UNSUBSCRIBE_LINK}}", "https://jiran.app/unsubscribe")
            html_body = html_body.replace("{{PRIVACY_LINK}}", "https://jiran.app/privacy")
            html_body = html_body.replace("{{TERMS_LINK}}", "https://jiran.app/terms")

            # Send email
            return await self.send_email(
                to_email=email,
                subject="Welcome to Jiran! 🎉",
                html_body=html_body,
                to_name=name,
            )

        except Exception as e:
            logger.error('Failed to send welcome email', extra={'email': email, 'error': str(e)}, exc_info=True)
            return False

    async def send_password_reset_email(self, email: str, reset_token: str, user_name: str | None = None) -> bool:
        """
        Send password reset email.

        Args:
            email: User's email address
            reset_token: Secure password reset token
            user_name: User's name (optional)

        Returns:
            True if email sent successfully
        """
        try:
            # Create reset link (deep link for mobile app)
            reset_link = f"jiran://reset-password?token={reset_token}"
            # Fallback web link
            web_reset_link = f"https://jiran.app/reset-password?token={reset_token}"

            # Simple HTML email (can create template later)
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 0; background-color: #f5f5f5;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; margin-top: 40px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #D4A745 0%, #C1440E 100%); padding: 40px 20px; text-align: center;">
            <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700;">Reset Your Password</h1>
        </div>

        <!-- Body -->
        <div style="padding: 40px 30px;">
            <p style="font-size: 16px; color: #333333; line-height: 1.6; margin: 0 0 20px;">
                {f"Hi {user_name}," if user_name else "Hello,"}
            </p>

            <p style="font-size: 16px; color: #333333; line-height: 1.6; margin: 0 0 20px;">
                We received a request to reset your password. Click the button below to create a new password:
            </p>

            <!-- Reset Button -->
            <div style="text-align: center; margin: 30px 0;">
                <a href="{web_reset_link}" style="display: inline-block; background: linear-gradient(135deg, #D4A745 0%, #C1440E 100%); color: #ffffff; text-decoration: none; padding: 16px 40px; border-radius: 12px; font-weight: 600; font-size: 16px;">
                    Reset Password
                </a>
            </div>

            <p style="font-size: 14px; color: #666666; line-height: 1.6; margin: 20px 0 0;">
                Or copy and paste this link into your browser:
            </p>
            <p style="font-size: 14px; color: #D4A745; word-break: break-all; margin: 10px 0 20px;">
                {web_reset_link}
            </p>

            <p style="font-size: 14px; color: #999999; line-height: 1.6; margin: 30px 0 0; padding-top: 20px; border-top: 1px solid #eeeeee;">
                This link will expire in 1 hour. If you didn't request a password reset, please ignore this email.
            </p>
        </div>

        <!-- Footer -->
        <div style="background-color: #f9f9f9; padding: 20px; text-align: center; border-top: 1px solid #eeeeee;">
            <p style="font-size: 12px; color: #999999; margin: 0;">
                © 2025 Jiran. All rights reserved.
            </p>
        </div>
    </div>
</body>
</html>
            """.strip()

            # Send email
            return await self.send_email(
                to_email=email,
                subject="Reset Your Jiran Password",
                html_body=html_body,
                to_name=user_name,
            )

        except Exception as e:
            logger.error('Failed to send password reset email', extra={'email': email, 'error': str(e)}, exc_info=True)
            return False


# Global email service instance
email_service = EmailService()
