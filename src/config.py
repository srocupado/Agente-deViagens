import os
from dotenv import load_dotenv

load_dotenv()

# Trip parameters
ORIGIN = "BSB"
ADULTS = 2
MIN_DURATION_DAYS = 21
MAX_DURATION_DAYS = 30

# Japanese airports to search
JAPAN_AIRPORTS = ["TYO", "OSA", "NGO", "FUK", "SPK"]

# Months to search (Sep–Dec 2026)
SEARCH_MONTHS = ["2026-09", "2026-10", "2026-11", "2026-12"]

# Top N cheapest date pairs to drill into per destination
MAX_DATES_PER_DESTINATION = 3

# Number of offers to show in the final message
TOP_OFFERS = 5

# Amadeus API
AMADEUS_BASE_URL = "https://test.api.amadeus.com"
AMADEUS_AUTH_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"

# Secrets from environment
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
AMADEUS_CLIENT_ID = os.environ["AMADEUS_CLIENT_ID"]
AMADEUS_CLIENT_SECRET = os.environ["AMADEUS_CLIENT_SECRET"]
TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_WHATSAPP_FROM = os.environ["TWILIO_WHATSAPP_FROM"]
WHATSAPP_TO = os.environ["WHATSAPP_TO"]
