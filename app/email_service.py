"""Sends inquiry emails via SMTP. Configure with env vars:
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, INQUIRY_TO_EMAIL.
For Gmail: use an "App Password" (Google Account -> Security -> App passwords),
SMTP_HOST=smtp.gmail.com, SMTP_PORT=587.
If SMTP env vars are not set, sending is skipped (the inquiry is still saved
to the DB so nothing is lost) and a clear log line explains why.
"""
import os
import smtplib
import ssl
from email.mime.text import MIMEText

SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
INQUIRY_TO_EMAIL = os.environ.get("INQUIRY_TO_EMAIL", "pers1052@gmail.com")


def is_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def send_inquiry_email(name: str, from_email: str, message: str) -> tuple[bool, str]:
    """Returns (sent, detail)."""
    if not is_configured():
        return False, "SMTP not configured (set SMTP_HOST/SMTP_USER/SMTP_PASSWORD env vars) — inquiry was saved to the database only."

    body = f"이름: {name}\n이메일: {from_email}\n\n문의 내용:\n{message}"
    msg = MIMEText(body)
    msg["Subject"] = f"[프라하 여행가이드] 새 문의 - {name}"
    msg["From"] = SMTP_USER
    msg["To"] = INQUIRY_TO_EMAIL
    msg["Reply-To"] = from_email

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, [INQUIRY_TO_EMAIL], msg.as_string())
        return True, "sent"
    except Exception as e:
        return False, f"SMTP error: {e}"
