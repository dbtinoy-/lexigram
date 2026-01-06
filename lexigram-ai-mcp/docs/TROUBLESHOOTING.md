---
title: lexigram-ai-mcp Troubleshooting
description: Common errors, causes, and fixes
---

## MCPServer fails to start

**Error:** `MCPInitializationError: Failed to resolve MCP controller: MyController`

**Cause:** The controller class has constructor dependencies not registered in the DI container.

**Fix:** Ensure all dependencies of your `MCPController` subclass are registered in the container before the MCP provider boots.

```python
# Register missing dependencies
container.singleton(UserRepository, PostgresUserRepository(db=...))
```

## Tool call returns empty result

**Error:** No error, but `call_tool` returns `{}`

**Cause:** The `@tool`-decorated method returns `None` or an empty dict.

**Fix:** Always return an `MCPToolResult` or a dict with a `content` key.

```python
@tool("hello", description="Say hello")
async def hello(self) -> dict:
    return {"content": [{"type": "text", "text": "Hello!"}]}
```

## MCPTransportError: Request timed out

**Error:** `MCPTransportError: Request timed out after 30.0s: tools/list`

**Cause:** The remote MCP server took longer than `request_timeout` to respond.

**Fix:** Increase `request_timeout` in `MCPConfig` (server) or `MCPClient` constructor (client).

```yaml
ai_mcp:
  request_timeout: 60.0
```

## MCPProtocolError: Unexpected jsonrpc version

**Error:** `MCPProtocolError: Unexpected jsonrpc version in response`

**Cause:** The remote server returned a non-conforming JSON-RPC response.

**Fix:** Verify the external MCP server implements the MCP protocol correctly. Check that `Content-Type` is `application/json` and the response contains `"jsonrpc": "2.0"`.

## MCPMethodNotFoundError: Method not found on server

**Error:** `MCPMethodNotFoundError: Method not found on server: tools/get_weather`

**Cause:** The tool name does not exist on the remote server, or the server does not expose any tools.

**Fix:** Call `list_tools()` first to verify available tool names. Ensure the server's handler is configured.

```python
tools = await client.list_tools()
print(tools)  # Check available names
```

## Connector not appearing in tool list

**Cause:** The connector's required configuration is missing or empty (e.g. `root_dir: ""` for `FilesystemConnector`).

**Fix:** Provide the required configuration key. An empty string disables the connector.

```yaml
ai_mcp:
  connectors:
    filesystem:
      root_dir: "/workspace"
```

## SSE transport not working

**Error:** Client cannot connect to SSE endpoint.

**Cause 1:** `enable_sse` is `false` in config.

**Fix:** Set `enable_sse: true` or use `StdioTransport` instead.

**Cause 2:** The HTTP server (WebProvider) is not configured to expose the MCP path.

**Fix:** Ensure `WebProvider` is registered and the MCP endpoint path matches.

## Tool name conflict during registration

**Symptom:** `MCPToolCallError: Tool 'my_tool' already registered` or one tool silently overwrites another.

**Cause:** Two `@tool`-decorated methods or two connectors registered tools with the same name in the tool handler.

**Solution:** Ensure tool names are unique across all connectors and controllers. Use namespaced prefixes for different sources.

```python
@tool("filesystem_read", description="Read a file")
async def read_file(self, path: str) -> dict: ...

@tool("github_read", description="Read a GitHub file")
async def read_github(self, path: str) -> dict: ...
```

## MCPResourceError — Resource not found

**Symptom:** `MCPResourceError: Resource not found: file:///workspace/config.yaml`

**Cause:** The resource URI doesn't match any registered resource template or static resource.

**Solution:** List available resources with `resources/list` and verify the URI matches.

```python
resources = await client.list_resources()
print(resources)  # Check registered URIs
```

Resource URIs must follow the `{scheme}://{path}` format expected by the resource handler.

## SSE transport: incomplete handshake

**Symptom:** `MCPTransportError: SSE handshake failed: unexpected Content-Type` or `SSE endpoint returned status 404`

**Cause:** The HTTP server returned a non-SSE response — wrong path, missing event stream headers, or the SSE path is not exposed.

**Solution:** Verify the MCP path in `MCPConfig` matches the client URL. Ensure `enable_sse: true` is set and `WebProvider` exposes the path.

```yaml
ai_mcp:
  enable_sse: true
  path: /mcp        # Must match client URL exactly
```

## Stdio server process exits immediately

**Symptom:** `MCPTransportError: Stdio process exited with code 1 before sending initialize`

**Cause:** The command in `client_stdio_command` failed to start or crashed — wrong path, missing Python module, or import error.

**Solution:** Run the command directly in the terminal first. Use an absolute path or ensure the command is on `$PATH`. Check stderr for import errors.

```bash
$ python /path/to/server.py --mcp-stdio
```

```python
from lexigram.ai.mcp.client import MCPClient, StdioClientTransport

transport = StdioClientTransport(["python", "/abs/path/to/server.py"])
client = MCPClient(transport)
```

## Client-server protocol version mismatch

**Symptom:** `MCPProtocolError: Unsupported protocol version: 2025-03-26`

**Cause:** The client and server were built against different revisions of the MCP spec.

**Solution:** Upgrade both client and server to the same lexigram version. The current protocol version is `2024-11-05`.

```python
from lexigram.ai.mcp.server.core import MCP_PROTOCOL_VERSION
print(f"Server protocol: {MCP_PROTOCOL_VERSION}")
```

## Debug Tips

- Set `LOG_LEVEL=DEBUG` to see handler registration and transport activity.
- Call `app.health_check()` to get the MCP provider's health status.
- Use `MCPModule.stub()` in integration tests to avoid transport complexity.
