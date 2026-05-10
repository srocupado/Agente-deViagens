import time
import logging
import requests

logger = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search"

# Overrides and common suffixes for extracting short city names from airport names
_CITY_OVERRIDES = {
    "NRT": "Tóquio", "HND": "Tóquio", "KIX": "Osaka", "ITM": "Osaka",
    "NGO": "Nagoya", "FUK": "Fukuoka", "CTS": "Sapporo", "OKA": "Okinawa",
    "GRU": "São Paulo", "CGH": "São Paulo", "VCP": "Campinas",
    "GIG": "Rio de Janeiro", "SDU": "Rio de Janeiro",
    "BSB": "Brasília", "SSA": "Salvador", "FOR": "Fortaleza",
    "REC": "Recife", "MAN": "Manaus", "BEL": "Belém",
    "LAX": "Los Angeles", "JFK": "Nova York", "MIA": "Miami",
    "ORD": "Chicago", "ATL": "Atlanta", "DFW": "Dallas",
    "LHR": "Londres", "CDG": "Paris", "AMS": "Amsterdã",
    "FRA": "Frankfurt", "MAD": "Madri", "FCO": "Roma",
    "DXB": "Dubai", "DOH": "Doha", "IST": "Istambul",
    "SIN": "Singapura", "HKG": "Hong Kong", "ICN": "Seul",
    "PEK": "Pequim", "PVG": "Xangai", "BKK": "Bangkok",
    "SYD": "Sydney", "MEL": "Melbourne",
}

_NAME_SUFFIXES = (
    " International Airport", " Airport", " International", " Intl",
)

_DEFAULT_DESTINATION_AIRPORTS: set[str] = set()


def _city_name(airport_id: str, airport_name: str) -> str:
    if airport_id in _CITY_OVERRIDES:
        return _CITY_OVERRIDES[airport_id]
    if "/" in airport_name:
        return airport_name.split("/")[0].strip()
    for suffix in _NAME_SUFFIXES:
        if airport_name.endswith(suffix):
            return airport_name[: -len(suffix)].strip()
    return airport_name


def _summarize_legs(legs: list[dict]) -> dict:
    if not legs:
        return {}
    city_map: dict[str, str] = {}
    for leg in legs:
        for key in ("departure_airport", "arrival_airport"):
            ap = leg.get(key, {})
            code = ap.get("id", "")
            if code and code not in city_map:
                city_map[code] = _city_name(code, ap.get("name", ""))

    codes = (
        [legs[0]["departure_airport"]["id"]]
        + [leg["arrival_airport"]["id"] for leg in legs]
    )
    route = " → ".join(
        f"{c} ({city_map[c]})" if city_map.get(c) else c for c in codes
    )
    total_min = sum(leg.get("duration", 0) for leg in legs)
    airlines = list(dict.fromkeys(
        leg.get("airline", "") for leg in legs if leg.get("airline")
    ))
    return {
        "route": route,
        "airlines": airlines,
        "departure": legs[0]["departure_airport"].get("time", ""),
        "arrival": legs[-1]["arrival_airport"].get("time", ""),
        "duration_str": f"{total_min // 60}h{total_min % 60:02d}m",
        "num_stops": len(legs) - 1,
    }


def _build_card(
    *,
    dest_city: str,
    dest_airport: str,
    travel_class_label: str,
    price: float,
    per_person: float,
    outbound_date: str,
    return_date: str,
    nights_str: str,
    out: dict,
    ret: dict,
) -> str:
    if ret:
        volta_line = f"VOLTA:   {ret.get('route', '')}  [{ret.get('duration_str', '')}]"
    else:
        volta_line = "VOLTA:   (volta não consultada — verifique no Google Flights)"

    airlines_combined = list(dict.fromkeys(
        (out.get("airlines") or []) + (ret.get("airlines") or [])
    ))
    cia_str = ", ".join(airlines_combined)

    return (
        f"DESTINO: {dest_city} ({dest_airport})\n"
        f"CLASSE:  {travel_class_label}\n"
        f"PRECO:   R$ {price:,.0f} total  ·  R$ {per_person:,.0f}/pessoa\n"
        f"DATAS:   Ida {outbound_date}  Volta {return_date}  ({nights_str})\n"
        f"IDA:     {out.get('route', '')}  [{out.get('duration_str', '')}]\n"
        f"{volta_line}\n"
        f"CIA:     {cia_str}"
    )


class SerpAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


class SerpAPIBudgetExhausted(SerpAPIError):
    def __init__(self):
        super().__init__(0, "SerpApi call budget exhausted for this run")


class SerpAPIClient:
    def __init__(self, api_key: str):
        self._api_key = api_key

    def _request_with_retry(self, params: dict) -> requests.Response:
        for attempt in range(3):
            try:
                resp = requests.get(SERPAPI_URL, params=params, timeout=45)
                if resp.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning("Rate limited, waiting %ds", wait)
                    time.sleep(wait)
                    continue
                if resp.status_code >= 500:
                    wait = 2 ** attempt
                    logger.warning("Server error %d, retrying in %ds", resp.status_code, wait)
                    time.sleep(wait)
                    continue
                return resp
            except requests.RequestException as exc:
                if attempt == 2:
                    raise
                logger.warning("Request error, retrying: %s", exc)
                time.sleep(2 ** attempt)
        return resp  # type: ignore[return-value]

    def search_round_trip(
        self,
        departure_id: str,
        arrival_id: str,
        outbound_date: str,
        return_date: str,
        adults: int = 2,
        currency: str = "BRL",
        travel_class: int = 1,
        travel_class_label: str = "Econômica",
        destination_airports: set[str] | None = None,
        ranking: str = "price_then_stops",
        top_offers: int = 2,
        on_call=None,
    ) -> list[dict]:
        base_params = {
            "engine": "google_flights",
            "departure_id": departure_id,
            "arrival_id": arrival_id,
            "outbound_date": outbound_date,
            "return_date": return_date,
            "adults": adults,
            "currency": currency,
            "type": "1",
            "travel_class": travel_class,
            "hl": "en",
            "gl": "us",
            "api_key": self._api_key,
        }

        if on_call is not None and not on_call():
            raise SerpAPIBudgetExhausted()

        resp = self._request_with_retry(base_params)
        data = self._handle_response(resp, departure_id, arrival_id, outbound_date)
        if data is None:
            return []

        offers = self._parse_outbound_offers(
            data,
            outbound_date=outbound_date,
            return_date=return_date,
            arrival_id=arrival_id,
            adults=adults,
            travel_class_label=travel_class_label,
            destination_airports=destination_airports or _DEFAULT_DESTINATION_AIRPORTS,
        )
        self._sort_offers(offers, ranking)
        top = offers[:top_offers]

        for offer in top:
            token = offer.pop("_departure_token", None)
            if not token:
                logger.info("No departure_token for offer R$ %s — skipping return lookup", offer.get("price_brl"))
                offer["_card_meta"]["ret"] = {}
                continue
            if on_call is not None and not on_call():
                logger.warning(
                    "Budget exhausted before fetching return for offer R$ %s",
                    offer.get("price_brl"),
                )
                offer["_card_meta"]["ret"] = {}
                continue
            ret_summary = self._fetch_return_summary(base_params, token)
            offer["_card_meta"]["ret"] = ret_summary
            offer["total_stops"] = (
                offer["_card_meta"]["out"].get("num_stops", 0)
                + ret_summary.get("num_stops", 0)
            )

        for offer in top:
            meta = offer.pop("_card_meta")
            offer["card"] = _build_card(
                dest_city=meta["dest_city"],
                dest_airport=meta["dest_airport"],
                travel_class_label=travel_class_label,
                price=meta["price"],
                per_person=meta["per_person"],
                outbound_date=outbound_date,
                return_date=return_date,
                nights_str=meta["nights_str"],
                out=meta["out"],
                ret=meta["ret"],
            )

        return top

    def _handle_response(
        self,
        resp: requests.Response,
        departure_id: str,
        arrival_id: str,
        outbound_date: str,
    ) -> dict | None:
        if resp.status_code != 200:
            body = resp.json() if resp.content else {}
            error_msg = body.get("error", resp.text[:300])
            if resp.status_code == 400:
                logger.info("No results for %s→%s on %s", departure_id, arrival_id, outbound_date)
                return None
            raise SerpAPIError(resp.status_code, error_msg)

        data = resp.json()
        if "error" in data:
            raise SerpAPIError(0, data["error"])
        return data

    def _fetch_return_summary(self, base_params: dict, departure_token: str) -> dict:
        params = dict(base_params)
        params["departure_token"] = departure_token
        try:
            resp = self._request_with_retry(params)
            data = self._handle_response(
                resp,
                base_params["departure_id"],
                base_params["arrival_id"],
                base_params["outbound_date"],
            )
        except SerpAPIError as exc:
            logger.warning("Failed to fetch return legs: %s", exc)
            return {}
        if data is None:
            return {}

        candidates = data.get("best_flights", []) + data.get("other_flights", [])
        if not candidates:
            return {}
        first = candidates[0]
        legs = first.get("flights") or []
        if not legs:
            return {}
        return _summarize_legs(legs)

    @staticmethod
    def _sort_offers(offers: list[dict], ranking: str) -> None:
        if ranking == "price_only":
            offers.sort(key=lambda x: x.get("price_brl") or float("inf"))
        else:
            offers.sort(key=lambda x: (x.get("price_brl") or float("inf"), x.get("total_stops", 0)))

    @staticmethod
    def _parse_outbound_offers(
        data: dict,
        outbound_date: str,
        return_date: str,
        arrival_id: str,
        adults: int,
        travel_class_label: str,
        destination_airports: set[str],
    ) -> list[dict]:
        from datetime import datetime

        offers = []
        all_flights = data.get("best_flights", []) + data.get("other_flights", [])

        for item in all_flights:
            legs = item.get("flights", [])
            if not legs:
                continue

            dest_airport = legs[-1]["arrival_airport"]["id"]
            if dest_airport != arrival_id and destination_airports and dest_airport not in destination_airports:
                # Outbound terminus is not the requested destination — skip.
                continue

            dest_city = _city_name(dest_airport, legs[-1]["arrival_airport"].get("name", ""))
            out = _summarize_legs(legs)
            price = item.get("price", 0)
            per_person = price / adults if adults > 0 else price

            try:
                nights = (
                    datetime.strptime(return_date, "%Y-%m-%d") -
                    datetime.strptime(outbound_date, "%Y-%m-%d")
                ).days
                nights_str = f"{nights} noites"
            except Exception:
                nights_str = ""

            offers.append({
                "price_brl": price,
                "total_stops": out.get("num_stops", 0),
                "outbound_date": outbound_date,
                "return_date": return_date,
                "destination_airport": dest_airport,
                "destination_name": dest_city,
                "_departure_token": item.get("departure_token"),
                "_card_meta": {
                    "dest_city": dest_city,
                    "dest_airport": dest_airport,
                    "price": price,
                    "per_person": per_person,
                    "nights_str": nights_str,
                    "out": out,
                    "ret": {},
                },
            })

        return offers
