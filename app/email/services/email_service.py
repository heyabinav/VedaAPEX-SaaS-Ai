"""Email service using Brevo SMTP."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from ..config import EmailConfig

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via Brevo SMTP."""

    def __init__(self):
        """Initialize email service with Brevo SMTP configuration."""
        self.smtp_host = EmailConfig.BREVO_SMTP_HOST
        self.smtp_port = EmailConfig.BREVO_SMTP_PORT
        self.smtp_username = EmailConfig.BREVO_SMTP_USERNAME
        self.smtp_password = EmailConfig.BREVO_SMTP_PASSWORD
        self.email_from = EmailConfig.EMAIL_FROM

        if not self.smtp_username or not self.smtp_password:
            logger.warning("⚠️  Email service not configured - BREVO_SMTP credentials missing")

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_text: Optional[str] = None,
    ) -> bool:
        """
        Send email via Brevo SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            plain_text: Plain text fallback

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create email message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.email_from
            message["To"] = to_email

            # Add plain text alternative
            if plain_text:
                part1 = MIMEText(plain_text, "plain")
                message.attach(part1)

            # Add HTML version
            part2 = MIMEText(html_content, "html")
            message.attach(part2)

            # Connect to Brevo SMTP and send
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.email_from, to_email, message.as_string())

            logger.info(f"✅ Email sent successfully to {to_email}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("❌ SMTP authentication failed - Check credentials")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            return False

    def send_verification_email(
        self,
        to_email: str,
        username: str,
        verification_token: str,
    ) -> bool:
        """
        Send email verification link.

        Args:
            to_email: Recipient email address
            username: User's username
            verification_token: Verification token

        Returns:
            True if sent successfully, False otherwise
        """
        verification_link = (
            f"{EmailConfig.APP_BASE_URL}/api/v1/email/verify?token={verification_token}"
        )

        html_content = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ color: #333; text-align: center; }}
                    .button {{ 
                        display: inline-block;
                        background-color: #007bff;
                        color: white;
                        padding: 10px 20px;
                        text-decoration: none;
                        border-radius: 5px;
                        margin: 20px 0;
                    }}
                    .footer {{ color: #999; font-size: 12px; text-align: center; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 class="header">Welcome to VedaAPEX!</h1>
                    <p>Hi {username},</p>
                    <p>Thank you for registering. Please verify your email address by clicking the button below:</p>
                    <a href="{verification_link}" class="button">Verify Email</a>
                    <p>Or copy and paste this link in your browser:</p>
                    <p>{verification_link}</p>
                    <p>This link will expire in 24 hours.</p>
                    <div class="footer">
                        <p>If you didn't register an account, please ignore this email.</p>
                        <p>&copy; 2024 VedaAPEX. All rights reserved.</p>
                    </div>
                </div>
            </body>
        </html>
        """

        plain_text = f"""
Welcome to VedaAPEX!

Hi {username},

Thank you for registering. Please verify your email address by visiting:

{verification_link}

This link will expire in 24 hours.

If you didn't register an account, please ignore this email.

© 2024 VedaAPEX. All rights reserved.
        """

        return self.send_email(
            to_email=to_email,
            subject=EmailConfig.VERIFICATION_EMAIL_SUBJECT,
            html_content=html_content,
            plain_text=plain_text,
        )
