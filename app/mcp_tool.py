"""
mcp_server.py
-------------
MCP server that exposes the Banks & Banjo LLC HR chatbot as a single tool.

Transport: stdio (standard for local MCP clients like Cursor, Claude Desktop)
Framework: FastMCP — the official high-level MCP Python SDK layer.
           It auto-generates the tool schema from type hints and docstrings,
           handles the stdio message loop, and converts exceptions into
           well-formed MCP error responses.

To register with Cursor, add to your ~/.cursor/mcp.json:
  {
    "mcpServers": {
      "banks-banjo-hr": {
        "command": "python",
        "args": ["/absolute/path/to/mcp_server.py"],
        "env": {
          "GLEAN_INSTANCE": "support-lab",
          "GLEAN_DATASOURCE": "interviewds",
          "GLEAN_SEARCH_TOKEN": "...",
          "GLEAN_CLIENT_TOKEN": "..."
        }
      }
    }
  }

Or, if you're using a .env file, you can omit the env block and rely on
dotenv loading inside chatbot.py.
"""

from mcp.server.fastmcp import FastMCP
from typing import Optional
from chatbot import ask

# ── Server init ───────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="banks-banjo-hr",
    instructions=(
        "This tool answers questions about Banks & Banjo LLC internal HR "
        "policies. It retrieves information from indexed HR documents covering "
        "onboarding, PTO, benefits, org structure, and performance reviews."
    ),
)

# ── Tool definition ───────────────────────────────────────────────────────────

@mcp.tool()
def glean_chat(
    question: str,
    datasource: Optional[str] = None,
    top_k: Optional[int] = 5,
    include_citations: Optional[bool] = True,
) -> dict:
    """
    Ask a question about Banks & Banjo LLC internal HR policies.

    Searches indexed HR documents via Glean and returns a grounded answer
    with source citations. Covers onboarding, PTO, benefits, org structure,
    and performance/compensation.

    Args:
        question:          The natural-language question to answer (required).
        datasource:        Override the Glean datasource to search.
                           Defaults to the value in GLEAN_DATASOURCE env var.
        top_k:             Number of search results to retrieve and use as
                           context. Higher values = more context but slower.
                           Default: 5.
        include_citations: Whether to include source document references in
                           the response. Default: True.

    Returns:
        A dict with:
          - answer (str): The grounded answer from Glean Chat.
          - sources (list): Documents used, each with title, url, doc_id.
          - no_results (bool): True if no matching documents were found.
    """
    if not question or not question.strip():
        raise ValueError("'question' is required and cannot be empty.")

    result = ask(
        question=question.strip(),
        top_k=top_k or 5,
        datasource=datasource or None,
        include_citations=include_citations if include_citations is not None else True,
    )

    return result


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # stdio transport: the MCP client (Cursor, Claude Desktop, etc.) launches
    # this script as a subprocess and communicates over stdin/stdout.
    # Do NOT print anything to stdout in this file — it will corrupt the
    # MCP protocol stream. Use stderr for any debug output if needed.
    mcp.run(transport="stdio")
