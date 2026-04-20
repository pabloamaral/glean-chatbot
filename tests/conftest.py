import sys
import os
from pathlib import Path

# Ensure env vars are set before any app module is imported
os.environ.setdefault("GLEAN_INSTANCE", "test-instance")
os.environ.setdefault("GLEAN_CLIENT_TOKEN", "test-client-token")
os.environ.setdefault("GLEAN_INDEXING_TOKEN", "test-indexing-token")
os.environ.setdefault("GLEAN_ACT_AS_EMAIL", "test@example.com")

# Make app modules importable without installing the package
APP_DIR = str(Path(__file__).parent.parent / "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
