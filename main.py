import logging
import sys
from datetime import datetime, timezone

from src import config
from src.serpapi_client import SerpAPIClient
from src.agent import run_agent
from src.email_sender import send_email, EmailSendError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main() -> int:
    run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    logger.info("Flight search agent starting — %s", run_ts)

    serpapi = SerpAPIClient(config.SERPAPI_API_KEY)

    try:
        body = run_agent(serpapi, run_ts)
        logger.info("Agent completed. Message length: %d chars", len(body))
    except Exception as exc:
        logger.error("Agent failed: %s", exc, exc_info=True)
        body = f"Falha na execução em {run_ts}.\n\nDetalhe: {exc}"

    subject = f"✈️ Passagens BSB → Japão — {run_ts[:10]}"

    try:
        send_email(
            subject=subject,
            body=body,
            gmail_user=config.GMAIL_USER,
            gmail_app_password=config.GMAIL_APP_PASSWORD,
            recipient_email=config.RECIPIENT_EMAIL,
        )
    except EmailSendError as exc:
        logger.error("Email send failed: %s", exc, exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
