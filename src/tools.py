import json
import logging

from src.serpapi_client import SerpAPIClient, SerpAPIError
from src.trip_config import TripConfig

logger = logging.getLogger(__name__)

MAX_TOOL_RESULT_CHARS = 4000


def build_tools(trip_cfg: TripConfig) -> list[dict]:
    origin_codes = ", ".join(trip_cfg.origin_airports)
    dest_codes_list = trip_cfg.destination_airports[:10]
    dest_codes = ", ".join(dest_codes_list)
    if len(trip_cfg.destination_airports) > 10:
        dest_codes += ", and others"

    return [
        {
            "name": "search_flights",
            "description": (
                f"Search Google Flights (via SerpApi) for round-trip flights from "
                f"{trip_cfg.origin_label} ({origin_codes}) to {trip_cfg.destination_label} "
                f"({dest_codes}) in {trip_cfg.travel_class_label} class for "
                f"{trip_cfg.adults} adult(s). Returns the top {trip_cfg.returns_per_search} "
                f"flights with full outbound AND return itineraries, sorted by price (BRL). "
                f"Each call consumes up to {1 + trip_cfg.returns_per_search} SerpApi credits "
                f"(1 outbound search + {trip_cfg.returns_per_search} return lookups). "
                f"Run budget: {trip_cfg.max_serpapi_calls} credits. Vary departure_id and "
                f"outbound_date across calls to cover the full window and multiple destination "
                f"airports."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "departure_id": {
                        "type": "string",
                        "description": (
                            f"Origin airport IATA code. Choose from: {origin_codes}."
                        ),
                    },
                    "arrival_id": {
                        "type": "string",
                        "description": (
                            f"Destination airport IATA code. Choose from: {dest_codes}. "
                            f"Use specific airport codes only — do NOT use city codes."
                        ),
                    },
                    "outbound_date": {
                        "type": "string",
                        "description": (
                            f"Departure date in YYYY-MM-DD format. Must be between "
                            f"{trip_cfg.window_start.isoformat()} and {trip_cfg.window_end.isoformat()}."
                        ),
                    },
                    "return_date": {
                        "type": "string",
                        "description": (
                            f"Return date in YYYY-MM-DD format. Must be exactly "
                            f"{trip_cfg.nights} days after outbound_date."
                        ),
                    },
                },
                "required": ["departure_id", "arrival_id", "outbound_date", "return_date"],
            },
        }
    ]


class CallCounter:
    def __init__(self, limit: int):
        self.limit = limit
        self.count = 0

    def increment(self) -> bool:
        if self.count >= self.limit:
            return False
        self.count += 1
        return True


def _handle_search_flights(
    client: SerpAPIClient,
    trip_cfg: TripConfig,
    counter: "CallCounter",
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: str,
) -> list[dict]:
    try:
        return client.search_round_trip(
            departure_id=departure_id,
            arrival_id=arrival_id,
            outbound_date=outbound_date,
            return_date=return_date,
            adults=trip_cfg.adults,
            currency="BRL",
            travel_class=trip_cfg.travel_class_int,
            travel_class_label=trip_cfg.travel_class_label,
            destination_airports=set(trip_cfg.destination_airports),
            ranking=trip_cfg.ranking,
            returns_per_search=trip_cfg.returns_per_search,
            on_call=counter.increment,
        )
    except SerpAPIError as exc:
        logger.error("SerpAPIError in search_flights: %s", exc)
        return []
    except Exception as exc:
        logger.error("Unexpected error in search_flights: %s", exc)
        return []


def dispatch_tool(
    tool_name: str,
    tool_input: dict,
    serpapi_client: SerpAPIClient,
    trip_cfg: TripConfig,
    counter: CallCounter,
) -> str:
    try:
        if tool_name == "search_flights":
            if counter.count >= counter.limit:
                return json.dumps({
                    "error": (
                        f"SerpApi call budget exhausted ({counter.count}/{counter.limit}). "
                        f"Compile the email with results gathered so far."
                    )
                })
            result = _handle_search_flights(serpapi_client, trip_cfg, counter, **tool_input)
        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        serialized = json.dumps(result, ensure_ascii=False)
        if len(serialized) > MAX_TOOL_RESULT_CHARS:
            serialized = serialized[:MAX_TOOL_RESULT_CHARS] + "... [truncated]"
        return serialized
    except Exception as exc:
        logger.error("dispatch_tool error for %s: %s", tool_name, exc)
        return json.dumps({"error": str(exc)})
