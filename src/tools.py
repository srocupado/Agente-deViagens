import json
import logging
from src.serpapi_client import SerpAPIClient, SerpAPIError
from src import config

logger = logging.getLogger(__name__)

MAX_TOOL_RESULT_CHARS = 4000

TOOLS = [
    {
        "name": "search_flights",
        "description": (
            "Search Google Flights (via SerpApi) for round-trip flights from São Paulo Guarulhos (GRU) "
            "to a Japanese airport for specific departure and return dates. "
            "Returns flights sorted by total price in BRL for 2 adults. "
            "IMPORTANT: Each call consumes 1 SerpApi credit (100/month free). "
            "Make at most 2 calls per run, choosing the most informative date combinations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "arrival_id": {
                    "type": "string",
                    "description": (
                        "Specific airport IATA code for Japan destination. "
                        "Use 'NRT' (Tokyo Narita), 'HND' (Tokyo Haneda), 'KIX' (Osaka Kansai), "
                        "'NGO' (Nagoya), 'FUK' (Fukuoka). "
                        "Do NOT use city codes like TYO or OSA — they return no results."
                    ),
                },
                "outbound_date": {
                    "type": "string",
                    "description": "Departure date from GRU in YYYY-MM-DD format, e.g. '2026-09-20'",
                },
                "return_date": {
                    "type": "string",
                    "description": (
                        "Return date from Japan in YYYY-MM-DD format. "
                        "Must be 21–30 days after outbound_date, e.g. '2026-10-15'"
                    ),
                },
            },
            "required": ["arrival_id", "outbound_date", "return_date"],
        },
    }
]


def handle_search_flights(
    client: SerpAPIClient,
    arrival_id: str,
    outbound_date: str,
    return_date: str,
) -> list[dict]:
    try:
        return client.search_round_trip(
            departure_id=config.ORIGIN,
            arrival_id=arrival_id,
            outbound_date=outbound_date,
            return_date=return_date,
            adults=config.ADULTS,
            currency="BRL",
        )
    except SerpAPIError as exc:
        logger.error("SerpAPIError in search_flights: %s", exc)
        return []
    except Exception as exc:
        logger.error("Unexpected error in search_flights: %s", exc)
        return []


def dispatch_tool(tool_name: str, tool_input: dict, serpapi_client: SerpAPIClient) -> str:
    try:
        if tool_name != "search_flights":
            return f"Unknown tool: {tool_name}"

        offers = handle_search_flights(serpapi_client, **tool_input)

        if not offers:
            return "No flights found for this search."

        lines = [f"Found {len(offers)} flights. Pre-formatted cards below — copy each VERBATIM:\n"]
        for i, offer in enumerate(offers[:config.TOP_OFFERS], 1):
            lines.append(f"<<< CARD {i} >>>")
            lines.append(offer["card"])
            lines.append(f"<<< END CARD {i} >>>")
            lines.append("")

        result = "\n".join(lines)
        if len(result) > MAX_TOOL_RESULT_CHARS:
            result = result[:MAX_TOOL_RESULT_CHARS] + "\n... [truncated]"
        return result
    except Exception as exc:
        logger.error("dispatch_tool error for %s: %s", tool_name, exc)
        return f"Error: {exc}"
