import logging
import anthropic
from src.tools import TOOLS, dispatch_tool
from src.amadeus_client import AmadeusClient
from src import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""You are a flight search assistant helping two travelers find the cheapest
round-trip flights from Brasília (BSB) to Japan between September and December 2026.
The trip must be between {config.MIN_DURATION_DAYS} and {config.MAX_DURATION_DAYS} days long.

Your task:
1. For each Japanese airport ({', '.join(config.JAPAN_AIRPORTS)}) and each month
   (2026-09, 2026-10, 2026-11, 2026-12), call search_cheapest_dates to find the
   cheapest departure windows.
2. For the top {config.MAX_DATES_PER_DESTINATION} cheapest date pairs per destination
   (across all months combined), call search_flight_offers to get detailed offers.
3. After collecting all results, compile the {config.TOP_OFFERS} overall cheapest
   round-trip options and format them into a clear WhatsApp message.

Format the final message like this (plain text, no markdown, use line breaks):

✈️ TOP {config.TOP_OFFERS} PASSAGENS BSB → JAPÃO
━━━━━━━━━━━━━━━━━━━━━━━

For each option:
🏆 #N — [City/Airport]
💰 R$ [price] (2 adultos)
📅 Ida: [YYYY-MM-DD] | Volta: [YYYY-MM-DD]
🛫 Ida: BSB → [connection] → [destination] ([duration])
🛬 Volta: [destination] → [connection] → BSB ([duration])
✈️ Companhia: [airline]

Then a footer:
━━━━━━━━━━━━━━━━━━━━━━━
🤖 Agente de Viagens | [timestamp]

If a destination returns no results, skip it and continue.
Return ONLY the final formatted message. Do not include any explanation or code blocks."""


def run_agent(amadeus_client: AmadeusClient, run_timestamp: str) -> str:
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    system = SYSTEM_PROMPT.replace("[timestamp]", run_timestamp)

    messages = [
        {
            "role": "user",
            "content": (
                f"Please search for the cheapest round-trip flights from BSB to Japan "
                f"(Sep–Dec 2026, {config.MIN_DURATION_DAYS}–{config.MAX_DURATION_DAYS} days) "
                f"for {config.ADULTS} adults and return the formatted WhatsApp message."
            ),
        }
    ]

    iterations = 0
    max_iterations = 50

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

        # Append assistant turn
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Extract final text
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "Erro: agente não retornou texto final."

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info("Tool call: %s(%s)", block.name, list(block.input.keys()))
                    result_str = dispatch_tool(block.name, block.input, amadeus_client)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        # Unexpected stop reason
        break

    logger.warning("Agent reached max iterations (%d)", max_iterations)
    # Return whatever text the last assistant message had, if any
    for block in (response.content if response else []):
        if hasattr(block, "text") and block.text:
            return block.text
    return "Erro: agente atingiu o limite de iterações sem produzir resultado."
