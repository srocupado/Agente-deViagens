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

JAPAN_AIRPORTS = {
    "NRT", "HND", "KIX", "ITM", "NGO", "FUK", "CTS", "OKA",
    "KMJ", "OIT", "KOJ", "SDJ", "HIJ", "TAK",
}


def _city_name(airport_id: str, airport_name: str) -> str:
    """Return a short Portuguese city name for an airport."""
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
        "connections": codes[1:-1],
        "airlines": airlines,
        "flight_numbers": [leg.get("flight_number", "") for leg in legs],
        "departure": legs[0]["departure_airport"].get("time", ""),
        "arrival": legs[-1]["arrival_airport"].get("time", ""),
        "duration_str": f"{total_min // 60}h{total_min % 60:02d}m",
        "num_stops": len(legs) - 1,
    }


class SerpAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


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
    ) -> list[dict]:
        """Search Google Flights round-trip via SerpApi. Returns parsed flight list."""
        params = {
            "engine": "google_flights",
            "departure_id": departure_id,
            "arrival_id": arrival_id,
            "outbound_date": outbound_date,
            "return_date": return_date,
            "adults": adults,
            "currency": currency,
            "type": "1",  # round trip
            "hl": "en",
            "gl": "us",
            "api_key": self._api_key,
        }

        resp = self._request_with_retry(params)

        if resp.status_code != 200:
            body = resp.json() if resp.content else {}
            error_msg = body.get("error", resp.text[:300])
            if resp.status_code == 400:
                logger.info("No results for %s→%s on %s", departure_id, arrival_id, outbound_date)
                return []
            raise SerpAPIError(resp.status_code, error_msg)

        data = resp.json()
        if "error" in data:
            raise SerpAPIError(0, data["error"])

        return self._parse_results(data, outbound_date, return_date, arrival_id)

    @staticmethod
    def _parse_results(
        data: dict,
        outbound_date: str,
        return_date: str,
        arrival_id: str,
    ) -> list[dict]:
        offers = []
        all_flights = data.get("best_flights", []) + data.get("other_flights", [])

        for item in all_flights:
            flights = item.get("flights", [])
            if not flights:
                continue

            # Split outbound / return by detecting when we reach a Japanese airport.
            # Filtering by departure date is unreliable because connecting legs
            # depart on a different calendar day (e.g. GRU→LAX departs Oct-12,
            # LAX→NRT departs Oct-13 — only LAX shows up in an Oct-12 filter).
            outbound_legs: list[dict] = []
            return_legs: list[dict] = []
            reached_japan = False

            for leg in flights:
                arr_id = leg.get("arrival_airport", {}).get("id", "")
                if not reached_japan:
                    outbound_legs.append(leg)
                    if arr_id in JAPAN_AIRPORTS or arr_id == arrival_id:
                        reached_japan = True
                else:
                    return_legs.append(leg)

            dest_airport = (
                outbound_legs[-1]["arrival_airport"]["id"] if outbound_legs else arrival_id
            )
            dest_city = _city_name(
                dest_airport,
                outbound_legs[-1]["arrival_airport"].get("name", "") if outbound_legs else "",
            )

            offers.append({
                "price_brl": item.get("price", 0),
                "outbound_date": outbound_date,
                "return_date": return_date,
                "destination_airport": dest_airport,
                "destination_name": dest_city,
                "outbound": _summarize_legs(outbound_legs),
                "return_leg": _summarize_legs(return_legs),
                "carbon_emissions": item.get("carbon_emissions", {}).get("this_flight"),
            })

        offers.sort(key=lambda x: x.get("price_brl") or 0)
        return offers
