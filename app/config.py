from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SIGNING_SECRET = os.getenv("SIGNING_SECRET")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
COFFEE_CHANNEL_ID = os.getenv("COFFEE_CHANNEL_ID")