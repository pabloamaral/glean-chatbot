"""
chatbot.py
----------
Core chatbot workflow for the Banks & Banjo LLC internal HR assistant.

Pipeline:
  1. SEARCH  — query Glean Search API, scoped to our datasource, to retrieve
               the most relevant document snippets for the user's question.
  2. CHAT    — pass the question + retrieved snippets to Glean Chat API to
               generate a grounded, cited answer.
  3. RETURN  — structured dict with answer text + source list.

This module is intentionally kept as a plain function (ask()) with no I/O,
so it can be called identically from the CLI, MCP tool, or tests.

Authentication:
  - Search uses GLEAN_SEARCH_TOKEN via the REST API directly (requests).
  - Chat uses GLEAN_CLIENT_TOKEN via the official glean-api-client SDK.
    The SDK handles the correct base URL and auth header format for the
    Client API, which differs from the Indexing API.
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

GLEAN_INSTANCE   = os.environ["GLEAN_INSTANCE"]        # e.g. "support-lab"
SEARCH_TOKEN     = os.environ["GLEAN_SEARCH_TOKEN"]
CLIENT_TOKEN     = os.environ["GLEAN_CLIENT_TOKEN"]
DATASOURCE       = os.environ["GLEAN_DATASOURCE"]      # e.g. "interviewds"

# Client API base URL (used for both Search and Chat REST calls)
CLIENT_BASE_URL = f"https://{GLEAN_INSTANCE}-be.glean.com/rest/api/v1"

# ── Step 1: Search ────────────────────────────────────────────────────────────

def search(question: str, top_k: int = 5, datasource: str = None) -> list[dict]:
    """
    Query the Glean Search API and return a list of result dicts.

    We scope results to our datasource using a facetFilter on the "app" field.
    This ensures the chatbot only retrieves content from the Banks & Banjo LLC
    HR documents, not from any other connected data sources in the sandbox.

    Why search before chat?
    - Gives us explicit control over which docs are used as context.
    - Lets us return citations with real doc IDs, titles, and URLs.
    - Prevents the Chat API from pulling in unrelated content from the sandbox.

    Returns a list of dicts, each with:
      - title (str)
      - url (str)
      - snippet (str): the most relevant text excerpt from that document
      - doc_id (str): stable ID we assigned during indexing
    """
    ds = datasource or DATASOURCE

    payload = {
        "query": question,
        "pageSize": top_k,
        "requestOptions": {
            "facetFilters": [
                {
                    "fieldName": "app",
                    "values": [
                        {
                            "value": ds,
                            "relationType": "EQUALS",
                        }
                    ],
                }
            ]
        },
    }

    headers = {
        "Authorization": f"Bearer {SEARCH_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        f"{CLIENT_BASE_URL}/search",
        headers=headers,
        json=payload,
        timeout=15,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Search API error {response.status_code}: {response.text}"
        )

    data = response.json()
    results = data.get("results", [])

    if not results:
        return []

    parsed = []
    for r in results:
        doc = r.get("document", {})
        # Glean returns multiple snippets per result; take the first non-empty one
        snippets = r.get("snippets", [])
        snippet_text = ""
        for s in snippets:
            text = s.get("text", "").strip()
            if text:
                snippet_text = text
                break

        parsed.append({
            "title":   doc.get("title", "Untitled"),
            "url":     doc.get("url", ""),
            "doc_id":  doc.get("id", ""),
            "snippet": snippet_text,
        })

    return parsed


# ── Step 2: Chat ──────────────────────────────────────────────────────────────

def chat(question: str, search_results: list[dict]) -> str:
    """
    Call the Glean Chat API with the user's question and retrieved snippets.

    We build a single USER message that contains:
      - The question itself
      - The top search result snippets inline as context

    Why inject snippets into the message rather than relying on Chat alone?
    - Makes our retrieval explicit and auditable.
    - Ensures the answer is grounded in our specific indexed docs.
    - Lets us control exactly what context the model sees.

    The Chat API uses the Client token (not the Search or Indexing token).
    It uses a different auth header format — "Bearer" for the Client API.
    """
    # Build a context block from retrieved snippets
    if search_results:
        context_lines = []
        for i, r in enumerate(search_results, 1):
            context_lines.append(
                f"[Source {i}: {r['title']}]\n{r['snippet']}"
            )
        context_block = "\n\n".join(context_lines)

        message_text = (
            f"Using only the following internal Banks & Banjo LLC HR documents "
            f"as your source, please answer this question:\n\n"
            f"Question: {question}\n\n"
            f"Context from internal documents:\n\n{context_block}\n\n"
            f"Cite which document(s) you used in your answer."
        )
    else:
        # No search results — tell the model to say so rather than hallucinate
        message_text = (
            f"A user asked: '{question}'\n\n"
            f"No relevant internal Banks & Banjo LLC HR documents were found "
            f"for this question. Please let the user know and suggest they "
            f"contact People Operations at people@banksandbanjo.com."
        )

    payload = {
        "messages": [
            {
                "fragments": [
                    {"text": message_text}
                ],
                "author": "USER",
            }
        ],
        "saveChat": False,  # Don't persist to Glean chat history in sandbox
    }

    headers = {
        "Authorization": f"Bearer {CLIENT_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        f"{CLIENT_BASE_URL}/chat",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Chat API error {response.status_code}: {response.text}"
        )

    data = response.json()

    # Extract the text from the last assistant message fragment
    messages = data.get("messages", [])
    for msg in reversed(messages):
        if msg.get("author") in ("GLEAN_AI", "ASSISTANT", "BOT"):
            for fragment in msg.get("fragments", []):
                text = fragment.get("text", "").strip()
                if text:
                    return text

    # Fallback: try to get any text from the response
    return data.get("answer", {}).get("text", "No answer returned from Chat API.")


# ── Step 3: Compose final response ────────────────────────────────────────────

def ask(
    question: str,
    top_k: int = 5,
    datasource: str = None,
    include_citations: bool = True,
) -> dict:
    """
    Main entry point. Run the full search → chat → return pipeline.

    Returns a dict with:
      {
        "answer": str,           # The grounded answer from Glean Chat
        "sources": [             # The documents retrieved by Search
          {
            "title": str,
            "url": str,
            "doc_id": str,
          },
          ...
        ],
        "no_results": bool       # True if search returned nothing
      }

    Raises RuntimeError if either API call fails, so callers (MCP, CLI)
    can handle errors consistently.
    """
    print(f"\n[1/2] Searching Glean for: '{question}' (top_k={top_k})...")
    results = search(question, top_k=top_k, datasource=datasource)

    if not results:
        print("  → No search results found. Will ask Chat to handle gracefully.")
    else:
        print(f"  → Found {len(results)} result(s):")
        for r in results:
            print(f"     - {r['title']} ({r['doc_id']})")

    print("\n[2/2] Generating answer via Glean Chat...")
    answer_text = chat(question, results)
    print("  → Answer received.")

    # Build sources list — only include if we actually got results
    sources = []
    if include_citations and results:
        for r in results:
            sources.append({
                "title":  r["title"],
                "url":    r["url"],
                "doc_id": r["doc_id"],
            })

    return {
        "answer":     answer_text,
        "sources":    sources,
        "no_results": len(results) == 0,
    }


# ── CLI entrypoint ────────────────────────────────────────────────────────────

def _print_response(response: dict) -> None:
    """Pretty-print the chatbot response to stdout."""
    print("\n" + "=" * 60)
    print("ANSWER")
    print("=" * 60)
    print(response["answer"])

    if response["sources"]:
        print("\n" + "-" * 60)
        print("SOURCES")
        print("-" * 60)
        for i, s in enumerate(response["sources"], 1):
            print(f"  [{i}] {s['title']}")
            print(f"       ID : {s['doc_id']}")
            print(f"       URL: {s['url']}")

    if response["no_results"]:
        print("\n[Note: No matching documents found in the indexed datasource.]")

    print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python chatbot.py \"your question here\"")
        print("Example: python chatbot.py \"How much parental leave do I get?\"")
        sys.exit(1)

    question = " ".join(sys.argv[1:])

    try:
        result = ask(question)
        _print_response(result)
    except RuntimeError as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
