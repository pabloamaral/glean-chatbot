# Banks & Banjo LLC — Internal HR Chatbot

An enterprise chatbot prototype built on Glean's Indexing, Search, and Chat APIs.
Exposes a single MCP tool (`glean_chat`) that answers questions about internal HR
policies using a set of indexed company documents.

---

## Architecture & Data Flow

```
[HR Documents (.txt)]
        │
        ▼
1. INDEXING (one-time, run indexer.py)
   POST /api/index/v1/bulkindexdocuments
   → Pushes 5 HR docs into Glean datasource "interviewds"
        │
        ▼
2. USER QUESTION
   (via CLI, or MCP tool invoked by Cursor / Claude Desktop)
        │
        ▼
3. SEARCH  (chatbot.py → search())
   POST /rest/api/v1/search
   → Scoped to datasource via facetFilter on "app" field
   → Returns top-K ranked snippets with doc metadata
        │
        ▼
4. CHAT  (chatbot.py → chat())
   POST /rest/api/v1/chat
   → Question + retrieved snippets sent as a single USER message
   → Glean generates a grounded answer with explicit citations
        │
        ▼
5. RETURN
   { answer: str, sources: [{title, url, doc_id}], no_results: bool }
```

The MCP server (`mcp_server.py`) wraps step 2–5 as a single callable tool,
allowing any MCP-compatible client (Cursor, Claude Desktop) to invoke the
chatbot natively.

---

## Setup

### Prerequisites

- Python 3.10+
- Access to the Glean sandbox (credentials in `.env`)

### Install

```bash
git clone <your-repo>
cd banks-banjo-hr-chatbot

python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Tokens are pre-filled in .env.example for the sandbox
```

Environment variables used:

| Variable | Description |
|---|---|
| `GLEAN_INSTANCE` | Glean instance name (`support-lab`) |
| `GLEAN_DATASOURCE` | Datasource to index into and search (`interviewds`) |
| `GLEAN_INDEXING_TOKEN` | Token for the Indexing API |
| `GLEAN_SEARCH_TOKEN` | Token for the Search API |
| `GLEAN_CLIENT_TOKEN` | Token for the Chat API (Client API scope) |

---

## Usage

### Step 1 — Index the documents (one-time)

```bash
python indexer.py
```

This pushes all 5 HR documents into the Glean datasource. Documents typically
appear in search within a few minutes. Verify at https://app.glean.com.

### Step 2 — Run the chatbot (CLI)

```bash
python chatbot.py "How much parental leave do I get?"
python chatbot.py "What's the 401k match?"
python chatbot.py "Who do I contact for an IT issue?"
python chatbot.py "When is open enrollment?"
```

### Step 3 — Run as an MCP tool (Cursor / Claude Desktop)

Add the following to your MCP client config:

**Cursor** (`~/.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "banks-banjo-hr": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_server.py"]
    }
  }
}
```

The server reads credentials from `.env` automatically.
Then in Cursor, you can invoke the tool:

```
Use the glean_chat tool to answer: "What's the PTO policy?"
```

---

## Project Structure

```
.
├── README.md
├── design_note.md              # Architecture decisions and tradeoffs
├── .env.example                # Environment variable template
├── requirements.txt
├── indexer.py                  # One-time script: index docs into Glean
├── chatbot.py                  # Core pipeline: search → chat → return
├── mcp_server.py               # FastMCP server wrapping chatbot.py
├── documents/                  # Source HR documents
│   ├── 01_welcome_and_onboarding.txt
│   ├── 02_pto_and_leave_policy.txt
│   ├── 03_benefits_guide.txt
│   ├── 04_org_structure.txt
│   └── 05_performance_and_compensation.txt
└── tests/
    └── test_chatbot.py         # Smoke tests for the pipeline
```

---

## Assumptions

- **Sandbox permissions**: Documents are indexed with `allowAnonymousAccess: true`.
  In production, you'd use `allowedUsers` or `allowedGroups` tied to real identities,
  and pass the requesting user's email via the `X-Glean-ActAs` header on Search/Chat calls.

- **Indexing is async**: After running `indexer.py`, there is a processing delay
  (typically 1–5 minutes) before documents are discoverable. This is a Glean platform
  behavior, not a bug.

- **Single datasource**: The prototype scopes all search to one datasource. In a
  multi-team production deployment, you'd likely have one datasource per team or
  content type, with routing logic at the chatbot layer.

- **No conversation memory**: Each call to `ask()` is stateless. The Chat API
  supports multi-turn conversations via `chatId`, but this prototype treats every
  question as independent. Adding `save_chat=True` and threading `chatId` through
  would enable multi-turn support.
