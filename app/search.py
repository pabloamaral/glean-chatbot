import requests
from config import CLIENT_BASE_URL, CLIENT_HEADERS, DATASOURCE


def search(question: str, top_k: int = 5) -> list[dict]:
    """Search docs and return normalized result metadata."""

    payload = {
        "query": question,
        "pageSize": top_k,
        "requestOptions": {
            "datasourcesFilter": [DATASOURCE],
            "facetFilters": [
                {
                    "fieldName": "app",
                    "values": [
                        {"value": DATASOURCE, "relationType": "EQUALS"}
                    ],
                }
            ],
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

    parsed = []
    for r in results:
        doc = r.get("document", {})
        snippets = r.get("snippets", [])
        snippet_parts = [s.get("text", "").strip() for s in snippets if s.get("text", "").strip()]
        snippet_text = " … ".join(snippet_parts)
        parsed.append({
            "title": doc.get("title", "Untitled"),
            "url": doc.get("url", ""),
            "doc_id": doc.get("id", ""),
            "snippet": snippet_text,
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
