import json
import logging
from src.tequila_client import TequilaClient, TequilaAPIError

logger = logging.getLogger(__name__)

MAX_TOOL_RESULT_CHARS = 4000

TOOLS = [
    {
        "name": "search_flights",
        "description": (
            "Searches the Tequila (Kiwi.com) API for the cheapest round-trip flights "
            "from Brasília (BSB) to any airport in Japan (country code JP). "
            "Results are sorted by total price in BRL for 2 adults. "
            "Call with a broad date window first, then optionally narrow down by sub-period."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date_from": {
                    "type": "string",
                    "description": "Start of the departure date window in DD/MM/YYYY format, e.g. '01/09/2026'",
                },
                "date_to": {
                    "type": "string",
                    "description": "End of the departure date window in DD/MM/YYYY format, e.g. '30/11/2026'",
                },
                "return_from": {
                    "type": "string",
                    "description": "Start of the return date window in DD/MM/YYYY format, e.g. '22/09/2026'",
                },
                "return_to": {
                    "type": "string",
                    "description": "End of the return date window in DD/MM/YYYY format, e.g. '31/12/2026'",
                },
                "nights_in_dst_from": {
                    "type": "integer",
                    "description": "Minimum nights at destination (default 21)",
                    "default": 21,
                },
                "nights_in_dst_to": {
                    "type": "integer",
                    "description": "Maximum nights at destination (default 30)",
                    "default": 30,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 10)",
                    "default": 10,
                },
            },
            "required": ["date_from", "date_to", "return_from", "return_to"],
        },
    }
]


def handle_search_flights(
    client: TequilaClient,
    date_from: str,
    date_to: str,
    return_from: str,
    return_to: str,
    nights_in_dst_from: int = 21,
    nights_in_dst_to: int = 30,
    limit: int = 10,
) -> list[dict]:
    from src import config
    try:
        return client.search_flights(
            fly_from=config.ORIGIN,
            fly_to=config.DESTINATION,
            date_from=date_from,
            date_to=date_to,
            return_from=return_from,
            return_to=return_to,
            nights_in_dst_from=nights_in_dst_from,
            nights_in_dst_to=nights_in_dst_to,
            adults=config.ADULTS,
            curr="BRL",
            limit=limit,
        )
    except TequilaAPIError as exc:
        logger.error("TequilaAPIError in search_flights: %s", exc)
        return []
    except Exception as exc:
        logger.error("Unexpected error in search_flights: %s", exc)
        return []


def dispatch_tool(tool_name: str, tool_input: dict, tequila_client: TequilaClient) -> str:
    try:
        if tool_name == "search_flights":
            result = handle_search_flights(tequila_client, **tool_input)
        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        serialized = json.dumps(result, ensure_ascii=False)
        if len(serialized) > MAX_TOOL_RESULT_CHARS:
            serialized = serialized[:MAX_TOOL_RESULT_CHARS] + "... [truncated]"
        return serialized
    except Exception as exc:
        logger.error("dispatch_tool error for %s: %s", tool_name, exc)
        return json.dumps({"error": str(exc)})
