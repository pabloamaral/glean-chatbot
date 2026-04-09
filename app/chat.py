"""
-------
Calls the Glean Chat API to generate a grounded answer from a user's
question and retrieved search snippets.

Usage:
    from chat import chat
    answer = chat("How much parental leave?", search_results=[...])
"""

import requests
from config import CLIENT_BASE_URL, CLIENT_HEADERS


def chat(question: str, search_results: list[dict]) -> str:
    """
    Call the Glean Chat API and return a grounded answer as a string.

    Builds a single USER message containing the question and the retrieved
    search snippets as inline context. This makes retrieval explicit and
    auditable, and ensures the model cites the specific indexed documents
    rather than drawing on general training knowledge.

    No-results handling: if search_results is empty, the model is instructed
    to acknowledge the gap and direct the user to People Operations — rather
    than receiving empty context and potentially hallucinating an answer.

    Args:
        question:       The user's original question.
        search_results: List of result dicts from search.py, each with
                        title, url, doc_id, and snippet.

    Returns:
        The grounded answer text from Glean Chat.

    Raises:
        RuntimeError: If the Chat API returns a non-200 response.
    """
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
        # No results — instruct the model to say so rather than hallucinate
        message_text = (
            f"A user asked: '{question}'\n\n"
            f"No relevant internal Banks & Banjo LLC HR documents were found "
            f"for this question. Please let the user know and suggest they "
            f"contact People Operations at people@banksandbanjo.com."
        )

    payload = {
        "messages": [
            {
                "fragments": [{"text": message_text}],
                "author": "USER",
            }
        ],
        "saveChat": False,
        "stream": False,  # Don't persist to Glean chat history in sandbox
    }

    response = requests.post(
        f"{CLIENT_BASE_URL}/chat",
        headers=CLIENT_HEADERS,
        json=payload,
        timeout=120,
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

    # Fallback
    return data.get("answer", {}).get("text", "No answer returned from Chat API.")


if __name__ == "__main__":
    import sys

    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is the PTO policy?"
    print(f"Asking Chat (no search context): '{question}'\n")

    answer = chat(question, search_results=[])
    print(answer)
