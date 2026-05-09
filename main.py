import logging
import sys
from datetime import datetime, timezone

from src import config
from src.tequila_client import TequilaClient
from src.agent import run_agent
from src.whatsapp_sender import send_whatsapp, WhatsAppSendError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main() -> int:
    run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    logger.info("Flight search agent starting — %s", run_ts)

    tequila = TequilaClient(config.TEQUILA_API_KEY)

    try:
        message_body = run_agent(tequila, run_ts)
        logger.info("Agent completed. Message length: %d chars", len(message_body))
    except Exception as exc:
        logger.error("Agent failed: %s", exc, exc_info=True)
        message_body = (
            f"⚠️ Agente de Viagens — ERRO\n\n"
            f"Falha na execução em {run_ts}.\n\nDetalhe: {exc}"
        )

    try:
        send_whatsapp(
            body_text=message_body,
            account_sid=config.TWILIO_ACCOUNT_SID,
            auth_token=config.TWILIO_AUTH_TOKEN,
            from_number=config.TWILIO_WHATSAPP_FROM,
            to_number=config.WHATSAPP_TO,
        )
        logger.info("WhatsApp message sent to %s", config.WHATSAPP_TO)
    except WhatsAppSendError as exc:
        logger.error("WhatsApp send failed: %s", exc, exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
