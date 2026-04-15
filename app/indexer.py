import os
import uuid
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

GLEAN_INSTANCE = os.environ["GLEAN_INSTANCE"]
INDEXING_TOKEN = os.environ["GLEAN_INDEXING_TOKEN"]
DATASOURCE = "interviewds"
DOCUMENTS_DIR = Path(__file__).parent.parent / "data"

BASE_URL = f"https://{GLEAN_INSTANCE}-be.glean.com/api/index/v1"

HEADERS = {
    "Authorization": f"Bearer {INDEXING_TOKEN}",
    "Content-Type": "application/json",
}

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


def build_document(filename: str, content: str) -> dict:
    """Build one Glean document payload."""
    meta = DOC_METADATA[filename]
    doc_id = meta["id"]
    title = meta["title"]

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
            "allowAllDatasourceUsersAccess": True,
        },
    }


def load_documents() -> list[dict]:
    """Read all files in DOC_METADATA and build payload documents."""
    docs = []
    for filename in DOC_METADATA:
        filepath = DOCUMENTS_DIR / filename
        if not filepath.exists():
            print(f"  [WARN] File not found, skipping: {filepath}")
            continue
        content = filepath.read_text(encoding="utf-8")
        docs.append(build_document(filename, content))
        print(f"  [OK] Loaded: {filename}")
    return docs


def bulk_index(documents: list[dict]) -> None:
    """Upload documents in one bulk-index batch."""
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


def main() -> None:
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
