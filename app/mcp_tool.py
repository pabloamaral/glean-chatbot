from typing import Optional

from mcp.server.fastmcp import FastMCP
from chatbot import ask

mcp = FastMCP(
    name="banks-banjo-hr",
    instructions=(
        "This tool answers questions about Banks & Banjo LLC internal HR "
        "policies. It retrieves information from indexed HR documents covering "
        "onboarding, PTO, benefits, org structure, and performance reviews."
    ),
)

@mcp.tool()
def glean_chat(
    question: str,
    datasource: Optional[str] = None,
    top_k: Optional[int] = 5,
    include_citations: Optional[bool] = True,
) -> dict:
    """Answer a question using indexed HR docs."""
    if not question or not question.strip():
        raise ValueError("'question' is required and cannot be empty.")

    result = ask(
        question=question.strip(),
        top_k=top_k or 5,
        datasource=datasource or None,
        include_citations=include_citations if include_citations is not None else True,
    )

    return result

if __name__ == "__main__":
    mcp.run(transport="stdio")
