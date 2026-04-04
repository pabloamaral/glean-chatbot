# Design Note — Banks & Banjo LLC HR Chatbot

**Author:** Pablo Amaral
**Stack:** Python, Glean Indexing / Search / Chat APIs, FastMCP (stdio)

---

## How the Three APIs Are Used

### Glean Indexing API

Used in `indexer.py` as a one-time setup step to push five internal HR
documents into a custom Glean datasource (`interviewds`).

I used the `/bulkindexdocuments` endpoint rather than `/indexdocuments` because
this is a full, clean load of a fixed document set — not an incremental update.
Bulk indexing atomically replaces the entire datasource, so there's no risk of
stale documents persisting across re-runs. Each document carries a stable `id`
(e.g. `banks-banjo-hr-001`) so that re-running the indexer updates existing
documents rather than creating duplicates.

Documents are indexed with `allowAnonymousAccess: true` for the sandbox. In
production this would be replaced with explicit user or group-based ACLs, and
the requesting user's identity would be passed through API calls so Glean can
enforce permissions at retrieval time.

### Glean Search API

Used in `chatbot.py → search()` to retrieve the most relevant document snippets
for a user's question before passing them to Chat.

Results are scoped to the custom datasource using a `facetFilter` on the `"app"`
field. This ensures the chatbot only retrieves content from the indexed HR
documents, regardless of what else is connected in the sandbox environment.

The decision to call Search explicitly — rather than relying on Chat alone to
retrieve context — was intentional: it gives the application control over which
documents are used, enables reliable citation construction, and makes the
retrieval step auditable and debuggable independently of generation.

### Glean Chat API

Used in `chatbot.py → chat()` to generate a grounded natural-language answer.

The retrieved search snippets are injected directly into the user message as
inline context, alongside an instruction to cite which documents were used. This
pattern (sometimes called "retrieval-augmented generation" or RAG) grounds the
model's output in the actual indexed content rather than its general training
knowledge.

`saveChat` is set to `False` in the sandbox to avoid polluting shared chat
history. In production this would be `True` for audit logging and observability.

---

## End-to-End Flow

```
User question
    → Search API (facet-filtered to datasource, top-K results)
    → If no results: return graceful fallback, skip Chat
    → Chat API (question + snippets as context)
    → Return { answer, sources[], no_results }
```

The no-results path is handled explicitly: rather than sending empty context to
the Chat API and risking a hallucinated answer, the system instructs the model to
acknowledge that no relevant documents were found and direct the user to People
Operations. This avoids confident but fabricated responses.

---

## Key Tradeoffs and Limitations

**Explicit search vs. Chat-only**
Calling Search before Chat adds one API round-trip and slightly increases
latency. The tradeoff is worth it: we get precise control over context,
reliable source attribution, and the ability to short-circuit when search
returns nothing.

**Snippet injection vs. Glean's native grounding**
Glean's Chat API can ground against indexed content natively without explicit
context injection, but doing so gives less control over which specific documents
are cited and makes it harder to return structured source references to the
caller. Explicit injection makes the pipeline transparent and testable.

**Stateless conversations**
Each call to `ask()` is independent. The Chat API supports multi-turn
conversations via `chatId`, but implementing that requires the caller to persist
and thread state across requests — which is out of scope for this prototype. The
MCP tool interface could be extended to accept an optional `chat_id` parameter
to enable multi-turn support.

**Single datasource**
The prototype is scoped to one datasource. A production system serving multiple
teams would likely use separate datasources per team (or content domain), with
routing logic to select the right datasource based on the user's team, role, or
the question's topic.

**Async indexing delay**
After running `indexer.py`, documents are not immediately searchable. Glean
processes indexed content asynchronously, typically within a few minutes. This
is a known platform behavior that would need to be surfaced clearly in a
production pipeline (e.g. via a status-check endpoint or webhook).

**No authentication on MCP server**
The MCP server runs locally over stdio and inherits credentials from the
environment. In a production deployment (e.g. as an HTTP-hosted MCP server),
you'd add authentication to the server itself and ensure tokens are not
exposed in client configs.

---

## How I Would Productionize This

For the live session, the key extensions I'd discuss are:

- **Permissions**: Pass `X-Glean-ActAs: user@company.com` on Search and Chat
  requests so Glean enforces document-level ACLs per user.
- **Scaling**: The MCP tool and chatbot pipeline are stateless — scale
  horizontally behind a load balancer. The indexer becomes an event-driven job
  triggered by document changes.
- **Observability**: Structured logging on every search query (query text,
  result count, latency), every Chat call (latency, answer length), and a
  trace ID correlating the two. Alerts on high no-results rates signal
  indexing gaps.
- **Multi-team rollout**: Separate datasources per team with a routing layer;
  feature-flag the MCP tool per team; canary rollout with a feedback mechanism
  (thumbs up/down) to catch quality regressions early.

