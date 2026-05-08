from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.settings import settings

logger = logging.getLogger(__name__)


async def _send(to: str, subject: str, html: str) -> None:
    if not settings.smtp_host:
        # Email not configured — log the link so dev can still test flows
        logger.info("EMAIL (not sent — SMTP not configured)\nTo: %s\nSubject: %s\n%s", to, subject, html)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
        start_tls=True,
    )


async def send_verification_email(to: str, token: str) -> None:
    url = f"{settings.app_url}/auth/verify-email?token={token}"
    await _send(
        to=to,
        subject="Verify your Rough Draft account",
        html=f"""
        <p>Thanks for joining Rough Draft! Click the link below to verify your email address.</p>
        <p><a href="{url}">{url}</a></p>
        <p>If you didn't create an account, you can ignore this email.</p>
        """,
    )


async def send_reset_email(to: str, token: str) -> None:
    url = f"{settings.app_url}/auth/reset-password?token={token}"
    await _send(
        to=to,
        subject="Reset your Rough Draft password",
        html=f"""
        <p>We received a request to reset your password. Click the link below — it expires in 1 hour.</p>
        <p><a href="{url}">{url}</a></p>
        <p>If you didn't request this, you can safely ignore this email.</p>
        """,
    )
