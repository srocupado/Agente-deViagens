import os

from dotenv import load_dotenv

load_dotenv()

# Path to the user-editable trip configuration (YAML).
TRIP_CONFIG_PATH = os.getenv("TRIP_CONFIG_PATH", "trip_config.yml")

# Secrets from environment.
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SERPAPI_API_KEY = os.environ["SERPAPI_API_KEY"]
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT_EMAIL = os.environ["RECIPIENT_EMAIL"]
