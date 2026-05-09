import logging
import sys
from datetime import datetime, timezone

from src import config
from src.serpapi_client import SerpAPIClient
from src.email_sender import send_email, EmailSendError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# All date windows to explore (arrival_id, outbound_date, return_date).
# Each run picks 1 window rotating by run index → stays within 100 calls/month.
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
    """Rotate through windows 2x/day so each gets ~6 runs/month."""
    run_index = (now.day - 1) * 2 + (1 if now.hour >= 12 else 0)
    return _WINDOWS[run_index % len(_WINDOWS)]


def _build_email(offers: list[dict], run_ts: str) -> str:
    top = sorted(offers, key=lambda x: x.get("price_brl") or 0)[: config.TOP_OFFERS]
    lines = [
        f"✈️ TOP {config.TOP_OFFERS} PASSAGENS GRU → JAPÃO",
        f"Período: set–dez 2026 | 2 adultos | {config.MIN_NIGHTS}–{config.MAX_NIGHTS} noites",
        "Atenção: preços saindo de GRU (Guarulhos). Quem parte de BSB deve incluir BSB→GRU.",
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]
    for i, offer in enumerate(top, 1):
        lines.append(f"🏆 #{i}")
        lines.append(offer["card"])
        lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🤖 Agente de Viagens · {run_ts}")
    return "\n".join(lines)


def main() -> int:
    now = datetime.now(timezone.utc)
    run_ts = now.strftime("%Y-%m-%d %H:%M UTC")
    logger.info("Flight search starting — %s", run_ts)

    arrival_id, outbound_date, return_date = _pick_window(now)
    logger.info("Window: GRU→%s  %s → %s", arrival_id, outbound_date, return_date)

    serpapi = SerpAPIClient(config.SERPAPI_API_KEY)
    try:
        offers = serpapi.search_round_trip(
            departure_id=config.ORIGIN,
            arrival_id=arrival_id,
            outbound_date=outbound_date,
            return_date=return_date,
            adults=config.ADULTS,
            currency="BRL",
        )
        logger.info("Found %d offers", len(offers))
    except Exception as exc:
        logger.error("Search failed: %s", exc, exc_info=True)
        offers = []

    if offers:
        body = _build_email(offers, run_ts)
    else:
        body = (
            f"✈️ Agente de Viagens — {run_ts}\n\n"
            f"Nenhum resultado para GRU→{arrival_id} ({outbound_date} → {return_date}).\n"
            "Tente novamente mais tarde."
        )

    subject = f"✈️ Passagens GRU → Japão — {run_ts[:10]}"
    try:
        send_email(
            subject=subject,
            body=body,
            gmail_user=config.GMAIL_USER,
            gmail_app_password=config.GMAIL_APP_PASSWORD,
            recipient_email=config.RECIPIENT_EMAIL,
        )
        logger.info("Email sent to %s", config.RECIPIENT_EMAIL)
    except EmailSendError as exc:
        logger.error("Email send failed: %s", exc, exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
