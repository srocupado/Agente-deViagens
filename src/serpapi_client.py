import time
import logging
import requests

logger = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search"


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
        # SerpApi returns best_flights and other_flights
        all_flights = data.get("best_flights", []) + data.get("other_flights", [])

        for item in all_flights:
            flights = item.get("flights", [])
            if not flights:
                continue

            # SerpApi returns all legs (outbound + return) in a flat list;
            # for round-trips each item in best_flights is one complete itinerary.
            # Identify outbound vs return by departure date.
            outbound_legs = [
                f for f in flights
                if f.get("departure_airport", {}).get("time", "").startswith(outbound_date)
            ]
            return_legs = [
                f for f in flights
                if f.get("departure_airport", {}).get("time", "").startswith(return_date)
            ]

            def summarize_legs(legs: list[dict]) -> dict:
                if not legs:
                    return {}
                cities = (
                    [legs[0]["departure_airport"]["id"]]
                    + [leg["arrival_airport"]["id"] for leg in legs]
                )
                connections = cities[1:-1]
                total_min = sum(leg.get("duration", 0) for leg in legs)
                airlines = list(dict.fromkeys(leg.get("airline", "") for leg in legs))
                flight_numbers = [leg.get("flight_number", "") for leg in legs]
                return {
                    "route": " → ".join(cities),
                    "connections": connections,
                    "airlines": airlines,
                    "flight_numbers": flight_numbers,
                    "departure": legs[0]["departure_airport"].get("time", ""),
                    "arrival": legs[-1]["arrival_airport"].get("time", ""),
                    "duration_min": total_min,
                    "duration_str": f"{total_min // 60}h{total_min % 60:02d}m",
                    "num_stops": len(legs) - 1,
                }

            price = item.get("price", 0)
            out_summary = summarize_legs(outbound_legs)
            ret_summary = summarize_legs(return_legs)

            # destination city from the last outbound leg
            dest_airport = arrival_id
            dest_city = ""
            if outbound_legs:
                dest_airport = outbound_legs[-1].get("arrival_airport", {}).get("id", arrival_id)
                dest_city = outbound_legs[-1].get("arrival_airport", {}).get("name", "")

            offers.append({
                "price_brl": price,
                "outbound_date": outbound_date,
                "return_date": return_date,
                "destination_airport": dest_airport,
                "destination_name": dest_city,
                "outbound": out_summary,
                "return_leg": ret_summary,
                "carbon_emissions": item.get("carbon_emissions", {}).get("this_flight"),
            })

        # Sort by price ascending
        offers.sort(key=lambda x: x.get("price_brl") or 0)
        return offers
