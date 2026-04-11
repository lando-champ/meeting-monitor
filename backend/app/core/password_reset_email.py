"""Optional SMTP delivery for password reset links."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    host = (getattr(settings, "SMTP_HOST", "") or "").strip()
    if not host:
        return

    from_addr = (getattr(settings, "SMTP_FROM", "") or settings.SMTP_USER or "").strip()
    if not from_addr:
        logger.warning("SMTP_HOST set but SMTP_FROM/SMTP_USER empty; skip email")
        return

    msg = EmailMessage()
    msg["Subject"] = "Reset your MeetingAI password"
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.set_content(
        f"You requested a password reset.\n\nOpen this link (valid for a limited time):\n{reset_url}\n\n"
        "If you did not request this, you can ignore this email."
    )

    port = int(getattr(settings, "SMTP_PORT", 587) or 587)
    user = (getattr(settings, "SMTP_USER", "") or "").strip()
    password = getattr(settings, "SMTP_PASSWORD", "") or ""
    use_tls = bool(getattr(settings, "SMTP_USE_TLS", True))

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if use_tls:
            smtp.starttls()
        if user:
            smtp.login(user, password)
        smtp.send_message(msg)

    logger.info("Password reset email sent to %s", to_email)
