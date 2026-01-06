---
title: lexigram-ai-mcp Configuration
description: Every config key, type, default, and env-var override
---

Loaded from the `ai_mcp:` section of `application.yaml`. Environment variable prefix: `LEX_AI_MCP__`.

## MCPConfig

```yaml
ai_mcp:
  enabled: true
  host: "0.0.0.0"
  port: 8080
  path: "/mcp"
  enable_sse: true
  stdio_mode: false
  server_name: "lexigram-mcp"
  server_version: "1.0.0"
  cors_origins: []
  max_request_size: 1048576
  request_timeout: 30.0
  client_url: null
  client_stdio_command: []
  connectors:
    filesystem:
      root_dir: ""
      read_only: false
    github:
      token: ""
      api_url: "https://api.github.com"
    web_fetch:
      enabled: false
      max_content_bytes: 524288
      user_agent: "lexigram-mcp/1.0"
    web_search:
      provider: "brave"
      api_key: ""
      max_results: 10
    slack:
      bot_token: ""
      max_messages: 100
    google_drive:
      service_account_json: ""
      impersonated_email: ""
    sql:
      dsn: ""
      allowed_tables: []
      read_only: true
```

### Top-Level Keys

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `true` | `LEX_AI_MCP__ENABLED` | Enable the MCP server subsystem |
| `host` | `str` | `"0.0.0.0"` | `LEX_AI_MCP__HOST` | Host to bind to (HTTP transport) |
| `port` | `int` | `8080` | `LEX_AI_MCP__PORT` | Port to bind to (HTTP transport) |
| `path` | `str` | `"/mcp"` | `LEX_AI_MCP__PATH` | URL path for MCP endpoint |
| `enable_sse` | `bool` | `true` | `LEX_AI_MCP__ENABLE_SSE` | Enable Server-Sent Events |
| `stdio_mode` | `bool` | `false` | `LEX_AI_MCP__STDIO_MODE` | Use stdio instead of HTTP |
| `server_name` | `str` | `"lexigram-mcp"` | `LEX_AI_MCP__SERVER_NAME` | Server name for handshake |
| `server_version` | `str` | `"1.0.0"` | `LEX_AI_MCP__SERVER_VERSION` | Server version string |
| `cors_origins` | `list[str]` | `[]` | `LEX_AI_MCP__CORS_ORIGINS` | CORS allowed origins |
| `max_request_size` | `int` | `1048576` | `LEX_AI_MCP__MAX_REQUEST_SIZE` | Max request body bytes |
| `request_timeout` | `float` | `30.0` | `LEX_AI_MCP__REQUEST_TIMEOUT` | Request timeout seconds |
| `client_url` | `str \| None` | `null` | `LEX_AI_MCP__CLIENT_URL` | External MCP server URL (SSE) |
| `client_stdio_command` | `list[str]` | `[]` | `LEX_AI_MCP__CLIENT_STDIO_COMMAND` | Subprocess command for stdio client |

### Connectors Sub-Config

**Filesystem:**
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `root_dir` | `str` | `""` | Sandboxed root directory (empty = disabled) |
| `read_only` | `bool` | `false` | Disable write_file and mutating tools |

**GitHub:**
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `token` | `str` | `""` | GitHub personal access token |
| `api_url` | `str` | `"https://api.github.com"` | GitHub Enterprise API override |

**Web Fetch:**
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | `bool` | `false` | Enable web-fetch tool |
| `max_content_bytes` | `int` | `524288` | Max response body size |
| `user_agent` | `str` | `"lexigram-mcp/1.0"` | HTTP User-Agent header |

**Web Search:**
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `provider` | `str` | `"brave"` | Search provider (`brave`, `serpapi`, `google`) |
| `api_key` | `str` | `""` | API key for search provider |
| `max_results` | `int` | `10` | Max results per query |

**Slack:**
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `bot_token` | `str` | `""` | Slack bot OAuth token |
| `max_messages` | `int` | `100` | Max messages per channel history request |

**Google Drive:**
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `service_account_json` | `str` | `""` | Path to service-account credentials JSON |
| `impersonated_email` | `str` | `""` | Email to impersonate (optional) |

**SQL:**
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `dsn` | `str` | `""` | Database connection string |
| `allowed_tables` | `list[str]` | `[]` | Allowlisted table names |
| `read_only` | `bool` | `true` | Permit SELECT only |

## Env-var Override Example

```bash
LEX_AI_MCP__ENABLED=true \
LEX_AI_MCP__HOST="0.0.0.0" \
LEX_AI_MCP__PORT=9090 \
LEX_AI_MCP__STDIO_MODE=false \
LEX_AI_MCP__CONNECTORS__GITHUB__TOKEN="ghp_xxx" \
  python -m my_app
```
