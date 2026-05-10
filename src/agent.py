import logging

import anthropic

from src import config
from src.serpapi_client import SerpAPIClient
from src.tools import CallCounter, build_tools, dispatch_tool
from src.trip_config import TripConfig

logger = logging.getLogger(__name__)


def build_system_prompt(trip_cfg: TripConfig) -> str:
    origin_codes = ", ".join(trip_cfg.origin_airports)
    dest_codes = ", ".join(trip_cfg.destination_airports)
    window_label = f"{trip_cfg.window_start.isoformat()} a {trip_cfg.window_end.isoformat()}"

    return f"""You are a flight search assistant helping {trip_cfg.adults} traveler(s) find round-trip
flights from {trip_cfg.origin_label} ({origin_codes}) to {trip_cfg.destination_label} ({dest_codes}).
Trip duration: exactly {trip_cfg.nights} nights. Travel class: {trip_cfg.travel_class_label}.

## Search strategy

You have a limited SerpApi quota. Make at most {trip_cfg.max_serpapi_calls} calls per run.

Choose departure dates from the window {trip_cfg.window_start.isoformat()} to {trip_cfg.window_end.isoformat()}.
Return date must be exactly {trip_cfg.nights} days after departure.

Pick the most promising destination airport(s) to compare. Vary the dates slightly across runs
based on the run timestamp so the full window is explored over time.

IMPORTANT: Always use specific airport IATA codes ({dest_codes}). Do NOT use city codes
like TYO or OSA — they return no results in this API.

## Output format

After collecting results, compile the {trip_cfg.top_offers} cheapest unique options and format a
plain-text email body (no markdown asterisks, backticks, or bold syntax).

Use exactly this structure:

✈️ TOP {trip_cfg.top_offers} PASSAGENS — {trip_cfg.origin_label} → {trip_cfg.destination_label} ({trip_cfg.travel_class_label})
Período: {window_label} | {trip_cfg.adults} adulto(s) | {trip_cfg.nights} noites
(nota: passagens saindo de {trip_cfg.origin_label}; verifique deslocamento até o aeroporto)
━━━━━━━━━━━━━━━━━━━━━━━━━

For each option (cheapest first), copy the pre-formatted "card" field VERBATIM from the tool
result, prefixed with "🏆 #N":

🏆 #N
[card content from tool result]

━━━━━━━━━━━━━━━━━━━━━━━━━

Close with:
🤖 Agente de Viagens · [timestamp]

Rules:
- Route must list every airport in the itinerary (the card already does this)
- If no results are found, say so clearly with a short explanation
- Return ONLY the formatted message — no extra explanation or code blocks"""


def run_agent(
    serpapi_client: SerpAPIClient,
    run_timestamp: str,
    trip_cfg: TripConfig,
) -> str:
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    system = build_system_prompt(trip_cfg).replace("[timestamp]", run_timestamp)
    tools = build_tools(trip_cfg)
    counter = CallCounter(trip_cfg.max_serpapi_calls)

    messages = [
        {
            "role": "user",
            "content": (
                f"Current time: {run_timestamp}. "
                f"Search for the cheapest round-trip flights {trip_cfg.origin_label} → "
                f"{trip_cfg.destination_label} (window {trip_cfg.window_start.isoformat()} to "
                f"{trip_cfg.window_end.isoformat()}, {trip_cfg.nights} nights, "
                f"{trip_cfg.adults} adult(s), class {trip_cfg.travel_class_label}) and return "
                f"the formatted email body."
            ),
        }
    ]

    iterations = 0
    max_iterations = 10
    last_response = None

    while iterations < max_iterations:
        iterations += 1
        logger.info("Agent iteration %d", iterations)

        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            system=system,
            tools=tools,
            messages=messages,
        )
        last_response = response

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    logger.info("SerpApi calls used this run: %d/%d", counter.count, counter.limit)
                    return block.text
            return "Erro: agente não retornou texto final."

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info(
                        "Tool call: %s(departure=%s, arrival=%s, outbound=%s, return=%s)",
                        block.name,
                        block.input.get("departure_id"),
                        block.input.get("arrival_id"),
                        block.input.get("outbound_date"),
                        block.input.get("return_date"),
                    )
                    result_str = dispatch_tool(
                        block.name, block.input, serpapi_client, trip_cfg, counter
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        break

    logger.warning("Agent reached max iterations (%d)", max_iterations)
    logger.info("SerpApi calls used this run: %d/%d", counter.count, counter.limit)
    if last_response:
        for block in last_response.content:
            if hasattr(block, "text") and block.text:
                return block.text
    return "Erro: agente atingiu o limite de iterações sem produzir resultado."
