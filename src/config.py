import os
from dotenv import load_dotenv

load_dotenv()

# Trip parameters
ORIGIN = "BSB"
ADULTS = 2
MIN_NIGHTS = 21
MAX_NIGHTS = 30

# Japan airports to consider (TYO = Tokyo covers NRT+HND; OSA = Osaka covers KIX+ITM)
JAPAN_AIRPORTS = ["TYO", "OSA", "NGO", "FUK"]

# Search window: Sep–Nov departure (latest allows 21-day return by Dec 31)
SEARCH_WINDOW_START = "2026-09-01"
SEARCH_WINDOW_END = "2026-11-30"

# Number of offers to surface in the final message
TOP_OFFERS = 5

# Secrets from environment
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SERPAPI_API_KEY = os.environ["SERPAPI_API_KEY"]
TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_WHATSAPP_FROM = os.environ["TWILIO_WHATSAPP_FROM"]
WHATSAPP_TO = os.environ["WHATSAPP_TO"]
