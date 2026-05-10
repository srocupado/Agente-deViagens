import logging
import sys
from datetime import datetime, timezone

from src import config
from src.agent import run_agent
from src.email_sender import EmailSendError, send_email
from src.serpapi_client import SerpAPIClient
from src.trip_config import TripConfigError, load_trip_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main() -> int:
    run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    logger.info("Flight search agent starting — %s", run_ts)

    try:
        trip_cfg = load_trip_config(config.TRIP_CONFIG_PATH)
    except TripConfigError as exc:
        logger.error("Trip config error: %s", exc)
        body = (
            f"Falha ao carregar {config.TRIP_CONFIG_PATH} em {run_ts}.\n\n"
            f"Detalhe: {exc}\n\n"
            f"Edite o arquivo no GitHub e faça commit para corrigir."
        )
        subject = f"❌ Erro de configuração — {run_ts[:10]}"
        try:
            send_email(
                subject=subject,
                body=body,
                gmail_user=config.GMAIL_USER,
                gmail_app_password=config.GMAIL_APP_PASSWORD,
                recipient_email=config.RECIPIENT_EMAIL,
            )
        except EmailSendError as email_exc:
            logger.error("Email send failed: %s", email_exc, exc_info=True)
        return 1

    serpapi = SerpAPIClient(config.SERPAPI_API_KEY)

    try:
        body = run_agent(serpapi, run_ts, trip_cfg)
        logger.info("Agent completed. Message length: %d chars", len(body))
    except Exception as exc:
        logger.error("Agent failed: %s", exc, exc_info=True)
        body = f"Falha na execução em {run_ts}.\n\nDetalhe: {exc}"

    subject = (
        f"✈️ Passagens {trip_cfg.origin_label} → {trip_cfg.destination_label} "
        f"({trip_cfg.travel_class_label}) — {run_ts[:10]}"
    )

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
