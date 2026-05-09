import logging
import anthropic
from src.tools import TOOLS, dispatch_tool
from src.tequila_client import TequilaClient
from src import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""You are a flight search assistant helping two travelers find the cheapest
round-trip flights from Brasília (BSB) to Japan between September and December 2026.
Trip duration: {config.MIN_NIGHTS}–{config.MAX_NIGHTS} nights. Travelers: {config.ADULTS} adults.

Your task:
1. Call search_flights with the full window (01/09/2026–30/11/2026 departure,
   22/09/2026–31/12/2026 return, 21–30 nights) to get up to 10 results.
2. Optionally make a second call narrowing to a sub-period if useful (e.g. Oct–Nov only).
3. Compile the {config.TOP_OFFERS} overall cheapest unique options and format them
   as a WhatsApp message (plain text, no markdown asterisks or backticks).

Message format (use exactly these Unicode characters for visual structure):

✈️ TOP {config.TOP_OFFERS} PASSAGENS BSB → JAPÃO
Período: set–dez 2026 | 2 adultos | 21–30 noites
━━━━━━━━━━━━━━━━━━━━━━━━━

For each option (most affordable first):

🏆 #{rank} — {city} ({airport_code})
💰 R$ {total_price} (2 adultos) · R$ {per_adult}/pessoa
📅 Ida: {departure_date}   Volta: {return_date}  ({nights} noites)
🛫 Ida: {route_out}  ({duration_out})
🛬 Volta: {route_back}  ({duration_back})
✈️  {airlines}
🔗 {deep_link}

Then:
━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 Agente de Viagens · [timestamp]

Rules:
- Route format: BSB → GRU → NRT (list every connection city)
- If deep_link is empty, omit the 🔗 line
- If the API returns no results, say so clearly in the message
- Return ONLY the formatted message, no extra text or code blocks"""


def run_agent(tequila_client: TequilaClient, run_timestamp: str) -> str:
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    system = SYSTEM_PROMPT.replace("[timestamp]", run_timestamp)

    messages = [
        {
            "role": "user",
            "content": (
                f"Search for the cheapest round-trip flights BSB → Japan "
                f"(Sep–Dec 2026, {config.MIN_NIGHTS}–{config.MAX_NIGHTS} nights, "
                f"{config.ADULTS} adults) and return the formatted WhatsApp message."
            ),
        }
    ]

    iterations = 0
    max_iterations = 15
    last_response = None

    while iterations < max_iterations:
        iterations += 1
        logger.info("Agent iteration %d", iterations)

        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=messages,
        )
        last_response = response

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "Erro: agente não retornou texto final."

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info("Tool call: %s(%s)", block.name, list(block.input.keys()))
                    result_str = dispatch_tool(block.name, block.input, tequila_client)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        break

    logger.warning("Agent reached max iterations (%d)", max_iterations)
    if last_response:
        for block in last_response.content:
            if hasattr(block, "text") and block.text:
                return block.text
    return "Erro: agente atingiu o limite de iterações sem produzir resultado."
