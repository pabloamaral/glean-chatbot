"""
search.py
---------
Calls the Glean Search API to retrieve relevant document snippets
for a user's question, scoped to the Banks & Banjo LLC HR datasource.

API reference: https://developers.glean.com/api/client-api/search/overview
Endpoint: POST /rest/api/v1/search

Usage:
    from search import search
    results = search("How much parental leave do I get?", top_k=5)
"""

import requests
from config import CLIENT_BASE_URL, CLIENT_HEADERS, DATASOURCE


def search(question: str, top_k: int = 5, datasource: str = None) -> list[dict]:
    """
    Query the Glean Search API and return a list of result dicts.

    Datasource scoping: we use requestOptions.datasourcesFilter to restrict
    results to our indexed HR documents only. This is the purpose-built field
    for datasource filtering — simpler and more explicit than using facetFilters.

    Why search before chat?
    - Gives us explicit control over which docs are used as context.
    - Lets us return citations with real doc IDs, titles, and URLs.
    - Prevents Chat from pulling in unrelated content from the sandbox.

    Request shape (from Glean docs):
        {
            "query": str,
            "pageSize": int,
            "requestOptions": {
                "datasourcesFilter": [str],  # scope to our datasource
                "facetBucketSize": int        # controls facet aggregation size
            }
        }

    Response shape (from Glean docs):
        {
            "results": [
                {
                    "id": str,
                    "title": str,
                    "url": str,
                    "snippet": str,
                    "datasource": str,
                    "lastModified": str,
                    ...
                }
            ],
            "requestId": str
        }

    Args:
        question:   The user's natural-language question.
        top_k:      Max number of results to return. Default: 5.
        datasource: Override the datasource to search. Defaults to DATASOURCE
                    from config (set via GLEAN_DATASOURCE env var).

    Returns:
        List of dicts, each with:
          - title (str):   Document title.
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
            # datasourcesFilter: purpose-built field to scope results to
            # specific datasources. Equivalent to filtering by "app" facet
            # but cleaner and more explicit for our single-datasource use case.
            "datasourcesFilter": [ds],
            "facetBucketSize": 10,
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

    # Response schema: title, url, id, snippet are top-level fields on each
    # result object — not nested under a "document" sub-object.
    parsed = []
    for r in results:
        parsed.append({
            "title":   r.get("title", "Untitled"),
            "url":     r.get("url", ""),
            "doc_id":  r.get("id", ""),
            "snippet": r.get("snippet", ""),
        })

    return parsed


if __name__ == "__main__":
    import sys

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
