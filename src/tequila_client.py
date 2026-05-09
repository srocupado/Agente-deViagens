import time
import logging
import requests

logger = logging.getLogger(__name__)

TEQUILA_SEARCH_URL = "https://api.tequila.kiwi.com/v2/search"


class TequilaAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


class TequilaClient:
    def __init__(self, api_key: str):
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {"apikey": self._api_key}

    def _request_with_retry(self, params: dict) -> requests.Response:
        for attempt in range(3):
            try:
                resp = requests.get(
                    TEQUILA_SEARCH_URL,
                    headers=self._headers(),
                    params=params,
                    timeout=30,
                )
                if resp.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning("Rate limited, waiting %ds (attempt %d)", wait, attempt + 1)
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

    def search_flights(
        self,
        fly_from: str,
        fly_to: str,
        date_from: str,
        date_to: str,
        return_from: str,
        return_to: str,
        nights_in_dst_from: int = 21,
        nights_in_dst_to: int = 30,
        adults: int = 2,
        curr: str = "BRL",
        limit: int = 10,
    ) -> list[dict]:
        """Search round-trip flights and return parsed offer list sorted by price."""
        params = {
            "fly_from": fly_from,
            "fly_to": fly_to,
            "date_from": date_from,
            "date_to": date_to,
            "return_from": return_from,
            "return_to": return_to,
            "nights_in_dst_from": nights_in_dst_from,
            "nights_in_dst_to": nights_in_dst_to,
            "adults": adults,
            "curr": curr,
            "flight_type": "round",
            "sort": "price",
            "limit": limit,
        }

        resp = self._request_with_retry(params)

        if resp.status_code == 200:
            return self._parse_results(resp.json(), adults)

        if resp.status_code in (400, 404):
            logger.info("No results for %s→%s (%s–%s)", fly_from, fly_to, date_from, date_to)
            return []

        raise TequilaAPIError(resp.status_code, f"Tequila API error: {resp.text[:300]}")

    @staticmethod
    def _parse_results(raw: dict, adults: int) -> list[dict]:
        offers = []
        for item in raw.get("data", []):
            route = item.get("route", [])
            outbound_segs = [s for s in route if s.get("return") == 0]
            return_segs = [s for s in route if s.get("return") == 1]

            def summarize_segments(segs: list[dict]) -> dict:
                if not segs:
                    return {}
                stops = [s["cityFrom"] for s in segs] + [segs[-1]["cityTo"]]
                connections = stops[1:-1]
                airlines_on_leg = list(dict.fromkeys(s.get("airline", "") for s in segs))
                return {
                    "from": segs[0]["flyFrom"],
                    "to": segs[-1]["flyTo"],
                    "departure": segs[0].get("local_departure", "")[:16],
                    "arrival": segs[-1].get("local_arrival", "")[:16],
                    "connections": connections,
                    "airlines": airlines_on_leg,
                    "num_stops": len(segs) - 1,
                }

            duration = item.get("duration", {})
            out_dur_h = duration.get("departure", 0) // 3600
            out_dur_m = (duration.get("departure", 0) % 3600) // 60
            ret_dur_h = duration.get("return", 0) // 3600
            ret_dur_m = (duration.get("return", 0) % 3600) // 60

            price_total = item.get("price", 0)

            offers.append({
                "price_brl": f"{price_total:.2f}",
                "price_per_adult_brl": f"{price_total / adults:.2f}" if adults else f"{price_total:.2f}",
                "destination_city": item.get("cityTo", ""),
                "destination_airport": item.get("flyTo", ""),
                "nights_at_destination": item.get("nightsInDest"),
                "outbound": summarize_segments(outbound_segs),
                "return_leg": summarize_segments(return_segs),
                "outbound_duration": f"{out_dur_h}h{out_dur_m:02d}m",
                "return_duration": f"{ret_dur_h}h{ret_dur_m:02d}m",
                "airlines": item.get("airlines", []),
                "deep_link": item.get("deep_link", ""),
                "availability_seats": item.get("availability", {}).get("seats"),
            })

        return offers
