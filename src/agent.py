import logging
import anthropic
from src.tools import TOOLS, dispatch_tool
from src.serpapi_client import SerpAPIClient
from src import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""You are a flight search assistant. Search for cheap round-trip flights
from São Paulo Guarulhos (GRU) to Japan, Sep–Dec 2026, {config.ADULTS} adults,
{config.MIN_NIGHTS}–{config.MAX_NIGHTS} nights.

## Search strategy

SerpApi quota: 100 calls/month — make exactly 1 call per run using the
airport code and dates provided in the user message. Do not change the dates.
IMPORTANT: Use the exact airport code given (NRT, KIX, HND, NGO, FUK).
Do NOT use city codes like TYO or OSA — they return no results.

## Output format

The tool returns pre-formatted flight cards between <<< CARD N >>> markers.
Your ONLY job is to assemble the email by placing those cards between the header and footer below.
Copy each card CHARACTER FOR CHARACTER — do not change, reorder, translate, or reformat anything inside the cards.

Write exactly:

✈️ TOP {config.TOP_OFFERS} PASSAGENS GRU → JAPÃO
Período: set–dez 2026 | 2 adultos | {config.MIN_NIGHTS}–{config.MAX_NIGHTS} noites
Atenção: preços saindo de GRU (Guarulhos). Quem parte de BSB deve incluir BSB→GRU.
━━━━━━━━━━━━━━━━━━━━━━━━━

🏆 #1
[paste CARD 1 here, character for character]

🏆 #2
[paste CARD 2 here, character for character]

(continue for all cards)

━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 Agente de Viagens · [timestamp]

If no results: say so clearly. Return ONLY the final email — no explanation, no code blocks."""


def run_agent(
    serpapi_client: SerpAPIClient,
    run_timestamp: str,
    arrival_id: str,
    outbound_date: str,
    return_date: str,
) -> str:
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    system = SYSTEM_PROMPT.replace("[timestamp]", run_timestamp)

    messages = [
        {
            "role": "user",
            "content": (
                f"Current time: {run_timestamp}. "
                f"Search for round-trip flights GRU → {arrival_id} "
                f"departing {outbound_date}, returning {return_date} "
                f"({config.ADULTS} adults). "
                "Use exactly these dates — do not change them. "
                "Return the formatted email body."
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
                    logger.info(
                        "Tool call: %s(arrival_id=%s, outbound=%s, return=%s)",
                        block.name,
                        block.input.get("arrival_id"),
                        block.input.get("outbound_date"),
                        block.input.get("return_date"),
                    )
                    result_str = dispatch_tool(block.name, block.input, serpapi_client)
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
