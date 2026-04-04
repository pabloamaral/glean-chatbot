from pathlib import Path
"""
config.py
---------
Shared configuration for all Glean API calls.
Imported by search.py, chat.py, and indexer.py.
"""

import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

GLEAN_INSTANCE = os.environ["GLEAN_INSTANCE"]       # e.g. "support-lab"
CLIENT_TOKEN   = os.environ["GLEAN_CLIENT_TOKEN"]   # Global token, scope: Chat + Search
DATASOURCE     = os.environ["GLEAN_DATASOURCE"]     # e.g. "interviewds"

# Global tokens require X-Glean-ActAs so Glean knows which user's permissions
# to apply. In production this is the requesting user's email from their
# authenticated session. In the sandbox we use the admin login.
ACT_AS_EMAIL = os.environ.get("GLEAN_ACT_AS_EMAIL", "alex@glean-sandbox.com")

# Both Search and Chat are Client API endpoints — same base URL
CLIENT_BASE_URL = f"https://{GLEAN_INSTANCE}-be.glean.com/rest/api/v1"

# Shared headers used by both search.py and chat.py
CLIENT_HEADERS = {
    "Authorization": f"Bearer {CLIENT_TOKEN}",
    "X-Glean-ActAs": ACT_AS_EMAIL,
    "Content-Type": "application/json",
}
