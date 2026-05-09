import os
from dotenv import load_dotenv

load_dotenv()

# Trip parameters
ORIGIN = "GRU"  # Guarulhos — hub de todas as rotas Brasil→Japão
ADULTS = 2
MIN_NIGHTS = 21
MAX_NIGHTS = 30

# Japan airports — use specific airport codes, not city codes (TYO/OSA don't work in SerpApi)
JAPAN_AIRPORTS = ["NRT", "HND", "KIX", "NGO", "FUK"]

# Search window: Sep–Nov departure (latest allows 21-day return by Dec 31)
SEARCH_WINDOW_START = "2026-09-01"
SEARCH_WINDOW_END = "2026-11-30"

# Number of offers to surface in the final email
TOP_OFFERS = 5

# Secrets from environment
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SERPAPI_API_KEY = os.environ["SERPAPI_API_KEY"]
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT_EMAIL = os.environ["RECIPIENT_EMAIL"]
