import json
import logging
from src.amadeus_client import AmadeusClient, AmadeusAPIError

logger = logging.getLogger(__name__)

MAX_TOOL_RESULT_CHARS = 3000

TOOLS = [
    {
        "name": "search_cheapest_dates",
        "description": (
            "Searches Amadeus Flight Cheapest Date Search for the lowest-priced "
            "round-trip departure dates between BSB and a Japanese airport for a given "
            "month and trip duration range (21–30 days). "
            "Returns a list of date/price combinations sorted cheapest first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "IATA code of departure airport, e.g. 'BSB'",
                },
                "destination": {
                    "type": "string",
                    "description": "IATA code of destination airport, e.g. 'TYO'",
                },
                "year_month": {
                    "type": "string",
                    "description": "Month to search in YYYY-MM format, e.g. '2026-09'",
                },
                "min_duration": {
                    "type": "integer",
                    "description": "Minimum trip duration in days",
                    "default": 21,
                },
                "max_duration": {
                    "type": "integer",
                    "description": "Maximum trip duration in days",
                    "default": 30,
                },
            },
            "required": ["origin", "destination", "year_month"],
        },
    },
    {
        "name": "search_flight_offers",
        "description": (
            "Fetches detailed round-trip flight offers from Amadeus for a specific "
            "origin, destination, departure date, and return date. Returns up to 5 offers "
            "with airline, flight segments, layovers, and total price in BRL for 2 adults."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "IATA code of departure airport",
                },
                "destination": {
                    "type": "string",
                    "description": "IATA code of destination airport",
                },
                "departure_date": {
                    "type": "string",
                    "description": "Outbound departure date in YYYY-MM-DD format",
                },
                "return_date": {
                    "type": "string",
                    "description": "Return departure date in YYYY-MM-DD format",
                },
                "adults": {
                    "type": "integer",
                    "description": "Number of adult travelers",
                    "default": 2,
                },
            },
            "required": ["origin", "destination", "departure_date", "return_date"],
        },
    },
]


def _parse_offers(raw: dict) -> list[dict]:
    carriers = raw.get("dictionaries", {}).get("carriers", {})
    result = []
    for offer in raw.get("data", []):
        itineraries = offer.get("itineraries", [])
        outbound = itineraries[0] if len(itineraries) > 0 else {}
        inbound = itineraries[1] if len(itineraries) > 1 else {}

        def parse_segments(itin: dict) -> list[dict]:
            segs = []
            for seg in itin.get("segments", []):
                dep = seg.get("departure", {})
                arr = seg.get("arrival", {})
                segs.append({
                    "from": dep.get("iataCode"),
                    "to": arr.get("iataCode"),
                    "departure": dep.get("at"),
                    "arrival": arr.get("at"),
                    "carrier": carriers.get(seg.get("carrierCode", ""), seg.get("carrierCode")),
                    "flight": f"{seg.get('carrierCode')}{seg.get('number')}",
                })
            return segs

        out_segs = parse_segments(outbound)
        in_segs = parse_segments(inbound)
        connections_out = [s["to"] for s in out_segs[:-1]]
        connections_in = [s["to"] for s in in_segs[:-1]]

        price = offer.get("price", {})
        result.append({
            "price_brl": price.get("grandTotal", price.get("total")),
            "validating_airline": carriers.get(
                (offer.get("validatingAirlineCodes") or [""])[0], ""
            ),
            "outbound_duration": outbound.get("duration"),
            "return_duration": inbound.get("duration"),
            "outbound_segments": out_segs,
            "return_segments": in_segs,
            "connections_outbound": connections_out,
            "connections_return": connections_in,
        })
    return result


def handle_search_cheapest_dates(
    client: AmadeusClient,
    origin: str,
    destination: str,
    year_month: str,
    min_duration: int = 21,
    max_duration: int = 30,
) -> list[dict]:
    try:
        data = client.get_cheapest_dates(origin, destination, year_month, min_duration, max_duration)
        parsed = [
            {
                "destination": d.get("destination"),
                "departureDate": d.get("departureDate"),
                "returnDate": d.get("returnDate"),
                "price": d.get("price", {}).get("total"),
            }
            for d in data
            if d.get("price", {}).get("total")
        ]
        parsed.sort(key=lambda x: float(x["price"] or 0))
        return parsed
    except AmadeusAPIError as exc:
        logger.error("AmadeusAPIError in search_cheapest_dates: %s", exc)
        return []
    except Exception as exc:
        logger.error("Unexpected error in search_cheapest_dates: %s", exc)
        return []


def handle_search_flight_offers(
    client: AmadeusClient,
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    adults: int = 2,
) -> list[dict]:
    try:
        raw = client.search_flight_offers(origin, destination, departure_date, return_date, adults)
        return _parse_offers(raw)
    except AmadeusAPIError as exc:
        logger.error("AmadeusAPIError in search_flight_offers: %s", exc)
        return []
    except Exception as exc:
        logger.error("Unexpected error in search_flight_offers: %s", exc)
        return []


def dispatch_tool(tool_name: str, tool_input: dict, amadeus_client: AmadeusClient) -> str:
    try:
        if tool_name == "search_cheapest_dates":
            result = handle_search_cheapest_dates(amadeus_client, **tool_input)
        elif tool_name == "search_flight_offers":
            result = handle_search_flight_offers(amadeus_client, **tool_input)
        else:
            result = {"error": f"Unknown tool: {tool_name}"}
        serialized = json.dumps(result, ensure_ascii=False)
        if len(serialized) > MAX_TOOL_RESULT_CHARS:
            serialized = serialized[:MAX_TOOL_RESULT_CHARS] + "... [truncated]"
        return serialized
    except Exception as exc:
        logger.error("dispatch_tool error for %s: %s", tool_name, exc)
        return json.dumps({"error": str(exc)})
