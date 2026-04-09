# Banks & Banjo LLC — Internal HR Chatbot

An enterprise chatbot prototype built on Glean's Indexing, Search, and Chat APIs.
Exposes a single MCP tool (`glean_chat`) that answers questions about internal HR
policies using a set of indexed company documents.

---

## Architecture & Data Flow

```
[HR Documents (.txt) in data/]
        │
        ▼
1. INDEXING (one-time, run app/indexer.py)
   POST /api/index/v1/bulkindexdocuments
   → Pushes 5 HR docs into Glean datasource (e.g. interviewds)
        │
        ▼
2. USER QUESTION
   (via CLI, or MCP tool invoked by Cursor / Claude Desktop)
        │
        ▼
3. SEARCH  (app/chatbot.py → search())
   POST /rest/api/v1/search
   → Scoped to datasource via requestOptions.datasourcesFilter
   → Returns top-K ranked snippets with doc metadata
        │
        ▼
4. CHAT  (app/chatbot.py → chat())
   POST /rest/api/v1/chat
   → Question + retrieved snippets sent as a single USER message
   → Glean generates a grounded answer with explicit citations
        │
        ▼
5. RETURN
   { answer: str, sources: [{title, url, doc_id}], no_results: bool }
```

The MCP server (`app/mcp_tool.py`) wraps step 2–5 as a single callable tool,
allowing any MCP-compatible client (Cursor, Claude Desktop) to invoke the
chatbot natively.

---

## Setup

### Prerequisites

- Python 3.10+
- Access to the Glean sandbox (credentials in `.env`)

### Install

```bash
git clone <your-repo-url>
cd glean-chatbot   # or your clone directory name

python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Edit .env: set GLEAN_INSTANCE, GLEAN_DATASOURCE, tokens, and optional GLEAN_ACT_AS_EMAIL
```

Environment variables used:

| Variable | Description |
|---|---|
| `GLEAN_INSTANCE` | Glean instance name (e.g. `support-lab`) |
| `GLEAN_DATASOURCE` | Datasource to index into and search (e.g. `interviewds`) |
| `GLEAN_INDEXING_TOKEN` | Bearer token for the Indexing API (`app/indexer.py`) |
| `GLEAN_CLIENT_TOKEN` | Bearer token for the Client API — Search and Chat (`app/search.py`, `app/chat.py`) |
| `GLEAN_ACT_AS_EMAIL` | Optional. Email for `X-Glean-ActAs` (defaults to `alex@glean-sandbox.com` in code) |

---

## Usage

Run CLI commands from the **repository root** so paths to `data/` resolve correctly.

### Step 1 — Index the documents (one-time)

```bash
python app/indexer.py
```

This pushes all 5 HR documents from `data/` into the Glean datasource. Documents typically
appear in search within a few minutes. Verify at https://app.glean.com.

### Step 2 — Run the chatbot (CLI)

```bash
python app/chatbot.py "How much parental leave do I get?"
python app/chatbot.py "What's the 401k match?"
python app/chatbot.py "Who do I contact for an IT issue?"
python app/chatbot.py "When is open enrollment?"
```

### Step 3 — Run as an MCP tool (Cursor / Claude Desktop)

Add the following to your MCP client config. Use the **absolute path** to `app/mcp_tool.py` on your machine.

**Cursor** (`~/.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "banks-banjo-hr": {
      "command": "python",
      "args": ["/absolute/path/to/glean-chatbot/app/mcp_tool.py"]
    }
  }
}
```

The app loads `.env` from the repository root (next to `app/`), so keep your env file there.

Then in Cursor, you can invoke the tool:

```
Use the glean_chat tool to answer: "What's the PTO policy?"
```

---

## Project Structure

```
.
├── README.md
├── design.md                   # Architecture decisions and tradeoffs
├── .env.example                # Environment variable template
├── requirements.txt
├── app/
│   ├── config.py               # Shared Client API config and .env loading
│   ├── indexer.py              # One-time script: index docs into Glean
│   ├── search.py               # Glean Search API
│   ├── chat.py                 # Glean Chat API
│   ├── chatbot.py              # Pipeline: search → chat → return
│   └── mcp_tool.py             # FastMCP server wrapping chatbot
└── data/                       # Source HR documents (.txt)
    ├── 01_welcome_and_onboarding.txt
    ├── 02_pto_and_leave_policy.txt
    ├── 03_benefits_guide.txt
    ├── 04_org_structure.txt
    └── 05_performance_and_compensation.txt
```

---

## Assumptions

- **Sandbox permissions**: Documents are indexed with `allowAnonymousAccess: true`.
  In production, you'd use `allowedUsers` or `allowedGroups` tied to real identities,
  and set `GLEAN_ACT_AS_EMAIL` (or the caller identity) so `X-Glean-ActAs` on Search/Chat matches a real user.

- **Indexing is async**: After running `app/indexer.py`, there is a processing delay
  (typically 1–5 minutes) before documents are discoverable. This is a Glean platform
  behavior, not a bug.

- **Single datasource**: The prototype scopes all search to one datasource. In a
  multi-team production deployment, you'd likely have one datasource per team or
  content type, with routing logic at the chatbot layer.

- **No conversation memory**: Each call to `ask()` is stateless. The Chat API
  supports multi-turn conversations via `chatId`, but this prototype treats every
  question as independent. Adding `save_chat=True` and threading `chatId` through
  would enable multi-turn support.
