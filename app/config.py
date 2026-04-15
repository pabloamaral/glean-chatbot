from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

GLEAN_INSTANCE = os.environ["GLEAN_INSTANCE"]
CLIENT_TOKEN = os.environ["GLEAN_CLIENT_TOKEN"]
DATASOURCE = "interviewds"

ACT_AS_EMAIL = os.environ.get("GLEAN_ACT_AS_EMAIL", "alex@glean-sandbox.com")

CLIENT_BASE_URL = f"https://{GLEAN_INSTANCE}-be.glean.com/rest/api/v1"

CLIENT_HEADERS = {
    "Authorization": f"Bearer {CLIENT_TOKEN}",
    "X-Glean-ActAs": ACT_AS_EMAIL,
    "Content-Type": "application/json",
}
