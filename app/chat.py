import requests
from config import CLIENT_BASE_URL, CLIENT_HEADERS


def _build_message(question: str, search_results: list[dict]) -> str:
    if search_results:
        context_lines = [
            f"[Source {i}: {result['title']}]\n{result['snippet']}"
            for i, result in enumerate(search_results, 1)
        ]
        context_block = "\n\n".join(context_lines)

        return (
            f"You are an HR assistant for Banks & Banjo LLC. "
            f"Using the internal HR documents provided below as your primary source, "
            f"give a thorough and complete answer to the question. "
            f"Include all relevant details, policies, rules, and exceptions found in the documents. "
            f"Do not truncate or summarize important details.\n\n"
            f"Question: {question}\n\n"
            f"Context from internal documents:\n\n{context_block}\n\n"
            f"Cite which document(s) you used in your answer."
        )

    return (
        f"A user asked: '{question}'\n\n"
        f"No relevant internal Banks & Banjo LLC HR documents were found "
        f"for this question. Please let the user know and suggest they "
        f"contact People Operations at people@banksandbanjo.com."
    )


def _extract_answer(response_json: dict) -> str:
    messages = response_json.get("messages", [])
    for message in reversed(messages):
        if message.get("author") in ("GLEAN_AI", "ASSISTANT", "BOT"):
            for fragment in message.get("fragments", []):
                text = fragment.get("text", "").strip()
                if text:
                    return text
    return response_json.get("answer", {}).get("text", "No answer returned from Chat API.")


def chat(question: str, search_results: list[dict]) -> str:
    """Generate an answer with optional retrieved context."""
    message_text = _build_message(question=question, search_results=search_results)

    payload = {
        "messages": [
            {
                "fragments": [{"text": message_text}],
                "author": "USER",
            }
        ],
        "saveChat": False,
        "stream": False,
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

    return _extract_answer(response.json())


if __name__ == "__main__":
    import sys

    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is the PTO policy?"
    print(f"Asking Chat (no search context): '{question}'\n")

    answer = chat(question, search_results=[])
    print(answer)
