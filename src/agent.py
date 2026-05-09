import logging
import anthropic
from src.tools import TOOLS, dispatch_tool
from src.serpapi_client import SerpAPIClient
from src import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""You are a flight search assistant helping two travelers find the cheapest
round-trip flights from São Paulo (GRU) to Japan between September and December 2026.
Trip duration: {config.MIN_NIGHTS}–{config.MAX_NIGHTS} nights. Travelers: {config.ADULTS} adults.

## Search strategy

You have a limited SerpApi quota (100 calls/month). Make at most 2 calls per run.

Choose departure dates from the window {config.SEARCH_WINDOW_START} to {config.SEARCH_WINDOW_END}.
Return dates must be 21–30 days after departure, no later than 2026-12-31.

Suggested approach:
1. First call: NRT (Tokyo Narita) with a mid-October departure (e.g. 2026-10-10, return 2026-11-04 = 25 nights).
   October is typically cheaper for GRU→Japan routes.
2. Optional second call: KIX (Osaka Kansai) with a late-September departure
   (e.g. 2026-09-25, return 2026-10-20) if the first result seems expensive (> R$ 12.000/pessoa).

IMPORTANT: Always use specific airport codes — NRT, HND, KIX, NGO, FUK.
Do NOT use city codes like TYO or OSA — they return no results in this API.

Based on the run timestamp, vary the dates slightly to explore the full window over time.

## Output format

Each flight result has a pre-formatted "card" field. Your job:
1. Pick the {config.TOP_OFFERS} cheapest results (sorted by price_brl ascending).
2. Build the final email by copying each card VERBATIM between the header and footer below.
   Do NOT rewrite, summarize, or reformat the card content in any way.

Header (write exactly):
✈️ TOP {config.TOP_OFFERS} PASSAGENS GRU → JAPÃO
Período: set–dez 2026 | 2 adultos | {config.MIN_NIGHTS}–{config.MAX_NIGHTS} noites
Atenção: preços saindo de GRU (Guarulhos). Quem parte de BSB deve incluir BSB→GRU.
━━━━━━━━━━━━━━━━━━━━━━━━━

For each of the top {config.TOP_OFFERS} flights, write:
🏆 #N
[paste the card field here EXACTLY as returned by the tool, character by character]

Footer (write exactly):
━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 Agente de Viagens · [timestamp]

If no results: say so clearly and suggest trying again later.
Return ONLY the final email — no explanation or code blocks."""


def run_agent(serpapi_client: SerpAPIClient, run_timestamp: str) -> str:
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    system = SYSTEM_PROMPT.replace("[timestamp]", run_timestamp)

    messages = [
        {
            "role": "user",
            "content": (
                f"Current time: {run_timestamp}. "
                f"Search for the cheapest round-trip flights GRU → Japan "
                f"(Sep–Dec 2026, {config.MIN_NIGHTS}–{config.MAX_NIGHTS} nights, "
                f"{config.ADULTS} adults) and return the formatted email body."
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
