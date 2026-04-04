"""
indexer.py
----------
One-time script to index the Banks & Banjo LLC HR documents into a Glean datasource.

Uses the /bulkindexdocuments endpoint, which is the right choice here because:
- We're doing a full, clean load of all docs (not an incremental update)
- It guarantees any previously indexed stale docs are removed
- It's atomic: Glean treats the upload as a single batch

Flow:
  1. Read each .txt file from the documents/ directory
  2. Build a Glean DocumentDefinition for each file
  3. POST all docs to /bulkindexdocuments in a single request
     (isFirstPage=True, isLastPage=True since our set is small)
  4. Print status — success or error details
"""

import os
import uuid
import json
import requests
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# ── Config ────────────────────────────────────────────────────────────────────

GLEAN_INSTANCE = os.environ["GLEAN_INSTANCE"]          # e.g. "support-lab"
INDEXING_TOKEN = os.environ["GLEAN_INDEXING_TOKEN"]
DATASOURCE     = os.environ["GLEAN_DATASOURCE"]        # e.g. "interviewds"
DOCUMENTS_DIR  = Path(__file__).parent.parent / "data"

BASE_URL = f"https://{GLEAN_INSTANCE}-be.glean.com/api/index/v1"

HEADERS = {
    "Authorization": f"Bearer {INDEXING_TOKEN}",
    "Content-Type": "application/json",
}

# ── Document metadata ─────────────────────────────────────────────────────────
# Maps filename → (doc_id, title)
# Keeping this explicit makes it easy to add/change metadata without
# relying on filename parsing, and gives us stable IDs across re-runs.

DOC_METADATA = {
    "01_welcome_and_onboarding.txt": {
        "id": "banks-banjo-hr-001",
        "title": "Welcome to Banks & Banjo LLC — New Employee Onboarding Guide",
    },
    "02_pto_and_leave_policy.txt": {
        "id": "banks-banjo-hr-002",
        "title": "Banks & Banjo LLC Time Off & Leave Policy",
    },
    "03_benefits_guide.txt": {
        "id": "banks-banjo-hr-003",
        "title": "Banks & Banjo LLC Employee Benefits Guide",
    },
    "04_org_structure.txt": {
        "id": "banks-banjo-hr-004",
        "title": "Banks & Banjo LLC Organizational Structure & Team Directory",
    },
    "05_performance_and_compensation.txt": {
        "id": "banks-banjo-hr-005",
        "title": "Banks & Banjo LLC Performance Reviews & Compensation Guide",
    },
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def build_document(filename: str, content: str) -> dict:
    """
    Build a single Glean DocumentDefinition dict.

    Key fields:
    - datasource: which custom datasource this belongs to
    - objectType: a label for the type of content (used in Glean UI filters)
    - id: stable unique ID — must be consistent across re-runs so Glean
          updates rather than duplicates the document
    - title: shown in search results and citations
    - body: the full text content; mimeType text/plain is simplest and reliable
    - viewURL: Glean requires a URL; we use a fake internal URL since these
               are local files. In production this would be a real doc URL.
    - permissions.allowAnonymousAccess: true for the sandbox so any user
               (including the sandbox login) can see the docs. In production
               you'd list specific allowedUsers or allowedGroups instead.
    - updatedAt: ISO 8601 timestamp; helps Glean understand content freshness
    """
    meta = DOC_METADATA[filename]
    doc_id = meta["id"]
    title  = meta["title"]

    return {
        "datasource": DATASOURCE,
        "objectType": "HRDocument",
        "id": doc_id,
        "title": title,
        "body": {
            "mimeType": "text/plain",
            "textContent": content,
        },
        "viewURL": f"https://internal.banksandbanjo.com/hr/{doc_id}",
        "permissions": {
            "allowAnonymousAccess": True,
        },
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def load_documents() -> list[dict]:
    """Read all .txt files from documents/ and build Glean document dicts."""
    docs = []
    for filename, _ in DOC_METADATA.items():
        filepath = DOCUMENTS_DIR / filename
        if not filepath.exists():
            print(f"  [WARN] File not found, skipping: {filepath}")
            continue
        content = filepath.read_text(encoding="utf-8")
        docs.append(build_document(filename, content))
        print(f"  [OK] Loaded: {filename}")
    return docs


def bulk_index(documents: list[dict]) -> None:
    """
    POST all documents to Glean's /bulkindexdocuments endpoint.

    uploadId: a unique ID for this batch. Using a UUID means each run is a
              fresh batch. If you re-run the script, Glean will replace the
              previous batch cleanly.

    isFirstPage + isLastPage = True: tells Glean this is a single-request
              upload (no pagination needed for our small doc set).

    forceRestartUpload = True: ensures any in-progress upload from a previous
              failed run is discarded and this one starts fresh.
    """
    upload_id = str(uuid.uuid4())
    payload = {
        "uploadId": upload_id,
        "datasource": DATASOURCE,
        "isFirstPage": True,
        "isLastPage": True,
        "forceRestartUpload": True,
        "documents": documents,
    }

    print(f"\n→ Sending {len(documents)} documents to Glean...")
    print(f"  Datasource : {DATASOURCE}")
    print(f"  Upload ID  : {upload_id}")
    print(f"  Endpoint   : {BASE_URL}/bulkindexdocuments")

    response = requests.post(
        f"{BASE_URL}/bulkindexdocuments",
        headers=HEADERS,
        json=payload,
        timeout=30,
    )

    if response.status_code == 200:
        print("\n✓ Indexing successful!")
        print("  Note: Documents may take a few minutes to appear in search.")
        print("  Verify at: https://app.glean.com")
    else:
        print(f"\n✗ Indexing failed — HTTP {response.status_code}")
        try:
            error_body = response.json()
            print(f"  Error: {json.dumps(error_body, indent=2)}")
        except Exception:
            print(f"  Raw response: {response.text}")
        raise SystemExit(1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== Banks & Banjo LLC HR Document Indexer ===\n")
    print("Loading documents from ../data/...")

    documents = load_documents()

    if not documents:
        print("\n✗ No documents loaded. Check that ../data/ contains the .txt files.")
        raise SystemExit(1)

    print(f"\n  {len(documents)} document(s) ready to index.")
    bulk_index(documents)


if __name__ == "__main__":
    main()
