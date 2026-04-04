"""
search.py
---------
Calls the Glean Search API to retrieve relevant document snippets
for a user's question, scoped to the Banks & Banjo LLC HR datasource.

Usage:
    from search import search
    results = search("How much parental leave do I get?", top_k=5)
"""

import requests
from config import CLIENT_BASE_URL, CLIENT_HEADERS, DATASOURCE


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

    Args:
        question:   The user's natural-language question.
        top_k:      Max number of results to return. Default: 5.
        datasource: Override the datasource to search. Defaults to DATASOURCE
                    from config (set via GLEAN_DATASOURCE env var).

    Returns:
        List of dicts, each with:
          - title (str):   Document title shown in search results.
          - url (str):     Document view URL.
          - doc_id (str):  Stable ID assigned at indexing time.
          - snippet (str): Most relevant text excerpt from the document.

    Raises:
        RuntimeError: If the Search API returns a non-200 response.
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

    response = requests.post(
        f"{CLIENT_BASE_URL}/search",
        headers=CLIENT_HEADERS,
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


if __name__ == "__main__":
    import sys
    import json

    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is the PTO policy?"
    print(f"Searching for: '{question}'\n")

    results = search(question)

    if not results:
        print("No results found.")
    else:
        for i, r in enumerate(results, 1):
            print(f"[{i}] {r['title']} ({r['doc_id']})")
            print(f"     {r['snippet'][:120]}...")
            print()
