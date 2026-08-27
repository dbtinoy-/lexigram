# Plan: MCP Tool Server (`demos/mcp-tools`)

> Conventions: see wave-2 overview. Port 7090, pkg `mcp_tools`.

> **Task 0 — recon:** map `experimental/ai/lexigram-ai-mcp` server/client
> registration APIs (SSE transport mount point, tool/resource/prompt
> decorators or builders) and how it integrates with `WebModule` mounts.
> Decide: child MCP app mounted at `/mcp` vs same-app routes; record choice
> in `src/mcp_tools/server.py` docstring.

> **Blueprint:** the acceptance checklist in `specs/2026-08-25-demos-code-alignment.md` §6 applies to this demo end-to-end.

**Goal:** five deterministic tools + resource + prompt exposed over MCP SSE; inspector invokes them showing raw frames; self-agent answers questions through the client transport.
**Architecture:** NotesService domain → tool handlers; McpServerService registers with ai-mcp; InspectorProxy + frame ring buffer expose protocol traffic to browser; SelfAgentService uses ai-mcp client against own endpoint with keyword→tool policy.

### Task 1: Domain + tools — TDD
- [ ] Tests: notes create/search round-trip; unit conversions table (m↔ft, kg↔lb, c↔f); delay.echo respects ms (use injected clock/sleep seam); chaos.fail toggles error tool; each handler returns MCP content shape per package contract.
- [ ] Implement `NotesService`, `build_tools()` returning registered tool set. Gates green. Commit `✨ feat(demos): mcp tool domain`.

### Task 2: Server + frame capture
- [ ] Tests (ASGI): SSE handshake completes; `tools/list` → 5 entries with schemas; `tools/call convert.unit {10,m,ft}` result ≈ 32.8084; resources/read `notes://all` lists notes; chaos tool call surfaces protocol-level error frame.
- [ ] Wire `McpServerService` onto chosen mount; `FrameRingBuffer` records both directions (cap 200). Commit `✨ feat(demos): mcp server + frames`.

### Task 3: Inspector proxy + self-agent
- [ ] Tests: POST /api/invoke happy + error passthrough; /api/tools mirrors registry; agent flow "create note X then search X" performs ≥2 tool calls in trace and final answer contains id/title; unknown question yields explicit no-tool answer.
- [ ] Implement `InspectorProxyController`, `SelfAgentService` (deterministic policy table). Commit `✨ feat(demos): mcp inspector + self-agent`.

### Task 4: Console
- [ ] Tabs per spec; arg editor prefilled from schema; Run → result pane; Frames tab polls `/api/frames?since=` cursor; Agent tab renders numbered tool-call trace chips.
- [ ] Boot smoke incl. connecting Claude Desktop manually is documented in README (stdio command line), not required for gates. Commit `✨ feat(demos): mcp console`.

### Task 5: Fleet + docs registration
- [ ] Registry/Makefile/README rows; `make check-demos` green. Commit `📝 docs(demos): register mcp-tools`.
