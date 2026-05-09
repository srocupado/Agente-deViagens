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

# Date windows to rotate through (arrival_id, outbound_date, return_date).
# Each run picks one window → stays within 100 calls/month.
_WINDOWS = [
    ("NRT", "2026-09-15", "2026-10-10"),
    ("KIX", "2026-09-20", "2026-10-15"),
    ("NRT", "2026-10-01", "2026-10-26"),
    ("KIX", "2026-10-05", "2026-10-30"),
    ("NRT", "2026-10-10", "2026-11-04"),
    ("KIX", "2026-10-15", "2026-11-09"),
    ("NRT", "2026-10-20", "2026-11-14"),
    ("KIX", "2026-10-25", "2026-11-19"),
    ("NRT", "2026-11-01", "2026-11-26"),
    ("KIX", "2026-11-05", "2026-11-30"),
]


def _pick_window(now: datetime) -> tuple[str, str, str]:
    """Rotate 2x/day so each window gets ~6 runs/month."""
    run_index = (now.day - 1) * 2 + (1 if now.hour >= 12 else 0)
    return _WINDOWS[run_index % len(_WINDOWS)]


def main() -> int:
    now = datetime.now(timezone.utc)
    run_ts = now.strftime("%Y-%m-%d %H:%M UTC")
    logger.info("Flight search agent starting — %s", run_ts)

    arrival_id, outbound_date, return_date = _pick_window(now)
    logger.info("Window: GRU→%s  %s → %s", arrival_id, outbound_date, return_date)

    serpapi = SerpAPIClient(config.SERPAPI_API_KEY)

    try:
        body = run_agent(serpapi, run_ts, arrival_id, outbound_date, return_date)
        logger.info("Agent completed. Message length: %d chars", len(body))
    except Exception as exc:
        logger.error("Agent failed: %s", exc, exc_info=True)
        body = f"Falha na execução em {run_ts}.\n\nDetalhe: {exc}"

    subject = f"✈️ Passagens GRU → Japão — {run_ts[:10]}"

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
