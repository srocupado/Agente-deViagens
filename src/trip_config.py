from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from src.locations import (
    LocationNotFoundError,
    is_domestic,
    resolve_location,
)


VALID_CLASSES = {"economy", "premium_economy", "business", "first"}
VALID_RANKINGS = {"price_then_stops", "price_only"}

_CLASS_TO_SERPAPI = {
    "economy": 1,
    "premium_economy": 2,
    "business": 3,
    "first": 4,
}

_CLASS_LABEL_PT = {
    "economy": "Econômica",
    "premium_economy": "Premium Economy",
    "business": "Executiva",
    "first": "Primeira Classe",
}


class TripConfigError(Exception):
    pass


@dataclass(frozen=True)
class TripConfig:
    origin_airports: list[str]
    destination_airports: list[str]
    origin_label: str
    destination_label: str
    nights: int
    window_start: date
    window_end: date
    adults: int
    travel_class: str
    travel_class_int: int
    travel_class_label: str
    top_offers: int
    ranking: str
    max_serpapi_calls: int


def _parse_month(value, field: str) -> date:
    if not isinstance(value, str):
        raise TripConfigError(f"Campo '{field}' deve ser texto no formato YYYY-MM. Recebido: {value!r}.")
    try:
        year, month = value.split("-")
        return date(int(year), int(month), 1)
    except (ValueError, AttributeError) as exc:
        raise TripConfigError(f"Campo '{field}' inválido: '{value}'. Use YYYY-MM (ex.: '2026-09').") from exc


def _last_day_of_month(d: date) -> date:
    if d.month == 12:
        return date(d.year, 12, 31)
    next_month_first = date(d.year, d.month + 1, 1)
    return date.fromordinal(next_month_first.toordinal() - 1)


def load_trip_config(path: str | Path = "trip_config.yml") -> TripConfig:
    path = Path(path)
    if not path.exists():
        raise TripConfigError(f"Arquivo de configuração não encontrado: {path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        raise TripConfigError(f"YAML inválido em {path}: {exc}") from exc

    trip = data.get("trip") or {}
    search = data.get("search") or {}

    origin_raw = trip.get("origin")
    destination_raw = trip.get("destination")
    nights = trip.get("nights")
    window = trip.get("window") or {}
    adults = trip.get("adults", 2)

    if not origin_raw:
        raise TripConfigError("Campo 'trip.origin' é obrigatório.")
    if not destination_raw:
        raise TripConfigError("Campo 'trip.destination' é obrigatório.")
    if not isinstance(nights, int) or nights <= 0:
        raise TripConfigError(f"Campo 'trip.nights' deve ser inteiro positivo. Recebido: {nights!r}.")
    if not isinstance(adults, int) or adults < 1:
        raise TripConfigError(f"Campo 'trip.adults' deve ser inteiro >= 1. Recebido: {adults!r}.")

    window_start_month = _parse_month(window.get("start"), "trip.window.start")
    window_end_month = _parse_month(window.get("end"), "trip.window.end")
    window_end = _last_day_of_month(window_end_month)
    if window_start_month > window_end:
        raise TripConfigError(
            f"trip.window.start ({window.get('start')}) deve ser <= trip.window.end ({window.get('end')})."
        )

    try:
        origin_airports, origin_label = resolve_location(str(origin_raw))
        destination_airports, destination_label = resolve_location(str(destination_raw))
    except LocationNotFoundError as exc:
        raise TripConfigError(str(exc)) from exc

    travel_class = search.get("class", "economy")
    if travel_class not in VALID_CLASSES:
        raise TripConfigError(
            f"Campo 'search.class' inválido: '{travel_class}'. Use um de: {sorted(VALID_CLASSES)}."
        )

    if travel_class != "economy" and is_domestic(destination_airports):
        raise TripConfigError(
            f"Classe '{travel_class}' não está disponível para voos domésticos. "
            f"Configure 'class: economy' ou escolha um destino internacional."
        )

    top_offers = search.get("top_offers", 5)
    if not isinstance(top_offers, int) or top_offers < 1:
        raise TripConfigError(f"Campo 'search.top_offers' deve ser inteiro >= 1. Recebido: {top_offers!r}.")

    ranking = search.get("ranking", "price_then_stops")
    if ranking not in VALID_RANKINGS:
        raise TripConfigError(
            f"Campo 'search.ranking' inválido: '{ranking}'. Use um de: {sorted(VALID_RANKINGS)}."
        )

    max_calls = search.get("max_serpapi_calls", 2)
    if not isinstance(max_calls, int) or max_calls < 1:
        raise TripConfigError(f"Campo 'search.max_serpapi_calls' deve ser inteiro >= 1. Recebido: {max_calls!r}.")

    return TripConfig(
        origin_airports=origin_airports,
        destination_airports=destination_airports,
        origin_label=origin_label,
        destination_label=destination_label,
        nights=nights,
        window_start=window_start_month,
        window_end=window_end,
        adults=adults,
        travel_class=travel_class,
        travel_class_int=_CLASS_TO_SERPAPI[travel_class],
        travel_class_label=_CLASS_LABEL_PT[travel_class],
        top_offers=top_offers,
        ranking=ranking,
        max_serpapi_calls=max_calls,
    )
