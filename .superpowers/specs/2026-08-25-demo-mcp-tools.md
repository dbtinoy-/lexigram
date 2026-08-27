# Spec: MCP Tool Server

Slug `mcp-tools` · package `mcp_tools` · port 7090 (`MCP_PORT`)
Subsystems: `lexigram-ai-mcp` (server + client transports), `lexigram-web`

## Story

The hub page lists five registered MCP tools with their JSON schemas. A built-in
inspector invokes any tool with editable arguments and prints the raw protocol
frames below the result. Then the kicker: a mini chat box whose agent answers
questions by calling this very server through the MCP *client* transport —
Lexigram talking to Lexigram over Model Context Protocol.

## Domain

Small deterministic `NotesService` (in-memory, like other demos) plus two toy
tools chosen for zero external deps:

| Tool | Behaviour |
|---|---|
| `notes.create {title, body}` | create note, returns id |
| `notes.search {query}` | substring match over titles/bodies |
| `convert.unit {value, from, to}` | length/weight/temperature table |
| `delay.echo {ms, text}` | sleeps then echoes (shows async tools) |
| `chaos.fail {on}` | toggles a failing tool for error-path demos |

Plus one resource (`notes://all`) and one prompt template (`summarize-notes`).

## Architecture

- `ToolsController` — hub console pages/assets (vanilla JS).
- `McpServerService` — wraps `lexigram-ai-mcp` server registration of
  tools/resource/prompt over SSE transport at `/mcp/sse`; recon task maps the
  package's actual registration API (`McpModule.configure(...)` surface).
- `InspectorProxy` — server-side passthrough so the browser can invoke tools /
  read frames without its own MCP client: `POST /api/invoke {name, args}`,
  `GET /api/tools`, `GET /api/frames?since=` (ring buffer of raw JSON-RPC both
  directions).
- `SelfAgentService` — uses the ai-mcp **client** against our own SSE endpoint;
  `POST /api/agent {question}` runs a scripted tool-loop (deterministic choice
  policy: match keywords → tool) and streams nothing — returns final answer +
  trace of tool calls.

## Console

Header tabs: Tools | Inspector | Frames | Agent. Tools = schema cards.
Inspector = pick tool, JSON arg editor, Run, result pane. Frames = live
JSON-RPC log. Agent = question box + answer + numbered tool-call trace.

## Testing

Unit: each tool handler (happy + error via chaos tool); frame ring buffer.
Integration (ASGI): SSE handshake → tools/list returns 5 → tools/call
`convert.unit` round-trip; self-agent answers a notes question end-to-end.
Console smoke: import/boot.

## Non-goals

stdio transport demo in-browser (documented command instead); auth on MCP
endpoint; real LLM for the agent loop.
