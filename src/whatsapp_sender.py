import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)

MAX_MESSAGE_CHARS = 1600


class WhatsAppSendError(Exception):
    pass


def _split_message(text: str, max_chars: int = MAX_MESSAGE_CHARS) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    parts = []
    while text:
        if len(text) <= max_chars:
            parts.append(text)
            break
        split_at = text.rfind("\n", 0, max_chars)
        if split_at == -1:
            split_at = max_chars
        parts.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return parts


def send_whatsapp(
    body_text: str,
    account_sid: str,
    auth_token: str,
    from_number: str,
    to_number: str,
) -> None:
    client = Client(account_sid, auth_token)
    parts = _split_message(body_text)
    total = len(parts)

    try:
        for i, part in enumerate(parts, 1):
            text = f"[{i}/{total}]\n{part}" if total > 1 else part
            message = client.messages.create(
                from_=from_number,
                to=to_number,
                body=text,
            )
            logger.info("WhatsApp message sent: SID=%s (%d/%d)", message.sid, i, total)
    except TwilioRestException as exc:
        raise WhatsAppSendError(f"Twilio error: {exc}") from exc
