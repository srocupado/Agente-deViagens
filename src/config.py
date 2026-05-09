import os
from dotenv import load_dotenv

load_dotenv()

# Trip parameters
ORIGIN = "BSB"
DESTINATION = "JP"  # Tequila accepts country codes — covers all Japanese airports
ADULTS = 2
MIN_NIGHTS = 21
MAX_NIGHTS = 30

# Search window: Sep–Dec 2026 (DD/MM/YYYY — Tequila format)
DATE_FROM = "01/09/2026"
DATE_TO = "30/11/2026"   # latest departure that allows a 21-day trip ending by Dec 31
RETURN_FROM = "22/09/2026"  # earliest possible return (Sep 1 + 21 days)
RETURN_TO = "31/12/2026"

# Number of offers to surface in the final message
TOP_OFFERS = 5

# Secrets from environment
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TEQUILA_API_KEY = os.environ["TEQUILA_API_KEY"]
TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_WHATSAPP_FROM = os.environ["TWILIO_WHATSAPP_FROM"]
WHATSAPP_TO = os.environ["WHATSAPP_TO"]
