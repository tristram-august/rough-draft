from __future__ import annotations

import asyncio
import json
import logging
import urllib.error
import urllib.request

from app.settings import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def _send_via_resend_api(to: str, subject: str, html: str) -> None:
    """
    Blocking call — run via asyncio.to_thread.

    Uses Resend's HTTP API rather than their SMTP relay. Confirmed in
    production that outbound TCP to smtp.resend.com:587 times out (Railway
    doesn't route it) while outbound HTTPS works fine — the same failure
    mode PaaS platforms commonly have with raw SMTP ports. Resend's API key
    doubles as their documented SMTP password, so this reuses the existing
    SMTP_PASSWORD setting as the API bearer token; no new secret needed.
    """
    payload = json.dumps(
        {"from": settings.smtp_from, "to": [to], "subject": subject, "html": html}
    ).encode("utf-8")

    req = urllib.request.Request(
        RESEND_API_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.smtp_password}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        resp.read()


async def _send(to: str, subject: str, html: str) -> None:
    if not settings.smtp_password:
        # Email not configured — log the link so dev can still test flows
        logger.info("EMAIL (not sent — no Resend API key configured)\nTo: %s\nSubject: %s\n%s", to, subject, html)
        return

    try:
        await asyncio.to_thread(_send_via_resend_api, to, subject, html)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        logger.error("Resend API rejected email to %s (HTTP %s): %s", to, e.code, body)
        raise
    except urllib.error.URLError as e:
        logger.error("Resend API unreachable sending to %s: %s", to, e)
        raise


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


async def send_mock_draft_summary(to: str, summary: str, slot: int, rounds: int, value_index: float) -> None:
    """Mail a completed mock draft back to the person who ran it."""
    from html import escape

    value_str = f"{'+' if value_index >= 0 else ''}{value_index:.1f}"
    await _send(
        to=to,
        subject=f"Your mock draft — slot {slot}, {rounds} rounds",
        html=f"""
        <p>Here's the mock draft you just finished on Rough Draft Football.</p>
        <p><b>Draft slot:</b> {slot}<br/>
           <b>Rounds:</b> {rounds}<br/>
           <b>Value index:</b> {value_str}</p>
        <pre style="font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;
                    background:#f6f7f9;padding:12px;border-radius:8px;
                    white-space:pre-wrap;">{escape(summary)}</pre>
        <p><a href="{settings.app_url}/fantasy">Run another one</a></p>
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
