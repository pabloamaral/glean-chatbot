"""
chatbot.py
----------
Orchestrates the full pipeline for the Banks & Banjo LLC HR chatbot:

  1. search.py  — retrieve relevant docs from Glean Search API
  2. chat.py    — generate a grounded answer via Glean Chat API
  3. Return structured result with answer + citations

This module contains no API logic — it only composes the two steps.
Can be called from the CLI, the MCP server, or tests.
"""

import sys
from search import search
from chat import chat


def ask(
    question: str,
    top_k: int = 5,
    datasource: str = None,
    include_citations: bool = True,
) -> dict:
    """
    Run the full search → chat pipeline and return a structured response.

    Args:
        question:          The user's natural-language question.
        top_k:             Number of search results to use as context.
        datasource:        Override the Glean datasource to search.
        include_citations: Whether to include source references in the response.

    Returns:
        {
            "answer":     str,   # Grounded answer from Glean Chat
            "sources":    list,  # [{title, url, doc_id}] from Search
            "no_results": bool,  # True if Search returned nothing
        }
    """
    print(f"\n[1/2] Searching for: '{question}' (top_k={top_k})...")
    results = search(question, top_k=top_k, datasource=datasource)

    if not results:
        print("  → No results found. Chat will handle gracefully.")
    else:
        print(f"  → {len(results)} result(s) found:")
        for r in results:
            print(f"     - {r['title']} ({r['doc_id']})")

    print("\n[2/2] Generating answer via Glean Chat...")
    answer_text = chat(question, results)
    print("  → Answer received.")

    sources = []
    if include_citations and results:
        sources = [
            {"title": r["title"], "url": r["url"], "doc_id": r["doc_id"]}
            for r in results
        ]

    return {
        "answer":     answer_text,
        "sources":    sources,
        "no_results": len(results) == 0,
    }


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
    if len(sys.argv) < 2:
        print('Usage: python chatbot.py "your question here"')
        print('Example: python chatbot.py "How much parental leave do I get?"')
        sys.exit(1)

    question = " ".join(sys.argv[1:])

    try:
        result = ask(question)
        _print_response(result)
    except RuntimeError as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
