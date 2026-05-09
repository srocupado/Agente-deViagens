import smtplib
import logging
from email.message import EmailMessage

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


class EmailSendError(Exception):
    pass


def send_email(
    subject: str,
    body: str,
    gmail_user: str,
    gmail_app_password: str,
    recipient_email: str,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = recipient_email
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(gmail_user, gmail_app_password)
            smtp.send_message(msg)
        logger.info("Email sent to %s", recipient_email)
    except smtplib.SMTPException as exc:
        raise EmailSendError(f"SMTP error: {exc}") from exc
