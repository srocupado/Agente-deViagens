import logging
import anthropic
from src.tools import TOOLS, dispatch_tool
from src.serpapi_client import SerpAPIClient
from src import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""You are a flight search assistant helping two travelers find the cheapest
round-trip flights from Brasília (BSB) to Japan between September and December 2026.
Trip duration: {config.MIN_NIGHTS}–{config.MAX_NIGHTS} nights. Travelers: {config.ADULTS} adults.

## Search strategy

You have a limited SerpApi quota (100 calls/month). Make at most 2 calls per run.

Choose departure dates from the window {config.SEARCH_WINDOW_START} to {config.SEARCH_WINDOW_END}.
Return dates must be 21–30 days after departure, no later than 2026-12-31.

Suggested approach:
1. First call: TYO (Tokyo) with a mid-October departure (e.g. 2026-10-10, return 2026-11-04 = 25 nights).
   October is typically cheaper for BSB→Japan routes.
2. Optional second call: OSA (Osaka) with a late-September departure
   (e.g. 2026-09-25, return 2026-10-20) if the first result seems expensive (> R$ 12.000/pessoa).

Based on the run timestamp, vary the dates slightly to explore the full window over time.

## Output format

After collecting results, compile the {config.TOP_OFFERS} cheapest unique options and format a
WhatsApp message (plain text only — no markdown asterisks, backticks, or bold syntax).

Use exactly this structure:

✈️ TOP {config.TOP_OFFERS} PASSAGENS BSB → JAPÃO
Período: set–dez 2026 | 2 adultos | {config.MIN_NIGHTS}–{config.MAX_NIGHTS} noites
━━━━━━━━━━━━━━━━━━━━━━━━━

For each option (cheapest first):

🏆 #N — [Cidade] ([código])
💰 R$ [preço total] · R$ [preço/pessoa]/pessoa
📅 Ida: [YYYY-MM-DD]   Volta: [YYYY-MM-DD]
🛫 Ida: [rota completa ex: BSB → GRU → NRT] ([duração])
🛬 Volta: [rota completa ex: NRT → GRU → BSB] ([duração])
✈️  [companhias aéreas]

━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 Agente de Viagens · [timestamp]

Rules:
- Route must list every airport, e.g. BSB → GRU → NRT (not just origin and destination)
- If no results are found, say so clearly
- Return ONLY the formatted message — no extra explanation or code blocks"""


def run_agent(serpapi_client: SerpAPIClient, run_timestamp: str) -> str:
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    system = SYSTEM_PROMPT.replace("[timestamp]", run_timestamp)

    messages = [
        {
            "role": "user",
            "content": (
                f"Current time: {run_timestamp}. "
                f"Search for the cheapest round-trip flights BSB → Japan "
                f"(Sep–Dec 2026, {config.MIN_NIGHTS}–{config.MAX_NIGHTS} nights, "
                f"{config.ADULTS} adults) and return the formatted WhatsApp message."
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
