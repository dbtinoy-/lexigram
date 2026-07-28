"""lexigram-mcp — MCP Server for Lexigram Framework.

Canonical import paths
-----------------------
MCPServer:         from lexigram.ai.mcp import MCPServer
MCPClient:         from lexigram.ai.mcp import MCPClient
MCPConfig:        from lexigram.ai.mcp import MCPConfig
ToolHandler:      from lexigram.ai.mcp import ToolHandler
ResourceHandler:  from lexigram.ai.mcp import ResourceHandler
PromptHandler:    from lexigram.ai.mcp import PromptHandler
StdioTransport:   from lexigram.ai.mcp import StdioTransport
SSETransport:     from lexigram.ai.mcp import SSETransport
MCPModule:        from lexigram.ai.mcp import MCPModule
MCPProvider:       from lexigram.ai.mcp import MCPProvider

Quick Start
-----------

    from lexigram.ai.mcp import MCPServer, MCPModule
    from lexigram import LexigramApplication

    app = LexigramApplication(
        modules=[..., MCPModule()],
    )

    await app.run()
"""

from __future__ import annotations

import importlib.metadata
import pkgutil
from typing import TYPE_CHECKING, Any

__path__ = pkgutil.extend_path(__path__, __name__)

from lexigram.ai.mcp.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.ai.mcp import MCPModule  # type: ignore[attr-defined]
    from lexigram.ai.mcp.adapters import ToolRegistryAdapter
    from lexigram.ai.mcp.client.core import (
        MCPClient,
        MCPClientTransport,
        SSEClientTransport,
        StdioClientTransport,
    )
    from lexigram.ai.mcp.client.module import (
        MCPClientModule,
        MCPClientProvider,
        MCPClientRegistry,
        MCPConnection,
    )
    from lexigram.ai.mcp.config import MCPConfig
    from lexigram.ai.mcp.controllers import (
        ControllerPromptProvider,
        ControllerResourceProvider,
        ControllerToolProvider,
        MCPController,
        ModulePromptProvider,
        ModuleResourceProvider,
        ModuleToolProvider,
        ServiceToolProvider,
    )
    from lexigram.ai.mcp.decorators import (
        prompt,
        resource,
        tool,
    )
    from lexigram.ai.mcp.di.provider import MCPProvider
    from lexigram.ai.mcp.exceptions import (
        MCPError,
        MCPInitializationError,
        MCPMethodNotFoundError,
        MCPPromptError,
        MCPProtocolError,
        MCPResourceError,
        MCPToolCallError,
        MCPTransportError,
    )
    from lexigram.ai.mcp.hooks import (
        MCPServerStartedHook,
        MCPServerStoppedHook,
        MCPToolInvokedHook,
    )
    from lexigram.ai.mcp.protocols import (
        MCPPromptHandlerProtocol,
        MCPPromptProviderProtocol,
        MCPResourceHandlerProtocol,
        MCPResourceProviderProtocol,
        MCPServerProtocol,
        MCPToolHandlerProtocol,
        MCPToolProviderProtocol,
        MCPTransportProtocol,
    )
    from lexigram.ai.mcp.server import MCPServer
    from lexigram.ai.mcp.server.handlers import (
        PromptHandler,
        ResourceHandler,
        ToolHandler,
    )
    from lexigram.ai.mcp.transport import (
        AbstractTransport,
        SSETransport,
        StdioTransport,
    )
    from lexigram.ai.mcp.types import (
        MCPInitializeResult,
        MCPJSONRPCRequest,
        MCPJSONRPCResponse,
        MCPPrompt,
        MCPPromptMessage,
        MCPResource,
        MCPResourceContent,
        MCPServerCapabilities,
        MCPServerInfo,
        MCPToolDefinition,
        MCPToolResult,
    )

_LAZY_IMPORTS: dict[str, str] = {
    "AbstractTransport": "lexigram.ai.mcp.transport",
    "ControllerPromptProvider": "lexigram.ai.mcp.controllers",
    "ControllerResourceProvider": "lexigram.ai.mcp.controllers",
    "ControllerToolProvider": "lexigram.ai.mcp.controllers",
    # Hooks
    "MCPServerStartedHook": "lexigram.ai.mcp.hooks",
    "MCPServerStoppedHook": "lexigram.ai.mcp.hooks",
    "MCPToolInvokedHook": "lexigram.ai.mcp.hooks",
    "MCPController": "lexigram.ai.mcp.controllers",
    "MCPInitializeResult": "lexigram.ai.mcp.types",
    "MCPJSONRPCRequest": "lexigram.ai.mcp.types",
    "MCPJSONRPCResponse": "lexigram.ai.mcp.types",
    "MCPPrompt": "lexigram.ai.mcp.types",
    "MCPPromptMessage": "lexigram.ai.mcp.types",
    "MCPResource": "lexigram.ai.mcp.types",
    "MCPResourceContent": "lexigram.ai.mcp.types",
    "MCPServerCapabilities": "lexigram.ai.mcp.types",
    "MCPServerInfo": "lexigram.ai.mcp.types",
    "MCPToolDefinition": "lexigram.ai.mcp.types",
    "MCPToolResult": "lexigram.ai.mcp.types",
    "ModulePromptProvider": "lexigram.ai.mcp.controllers",
    "ModuleResourceProvider": "lexigram.ai.mcp.controllers",
    "ModuleToolProvider": "lexigram.ai.mcp.controllers",
    "ServiceToolProvider": "lexigram.ai.mcp.controllers",
    "MCPClient": "lexigram.ai.mcp.client.core",
    "MCPClientModule": "lexigram.ai.mcp.client.module",
    "MCPClientProvider": "lexigram.ai.mcp.client.module",
    "MCPClientRegistry": "lexigram.ai.mcp.client.module",
    "MCPConnection": "lexigram.ai.mcp.client.module",
    "MCPClientTransport": "lexigram.ai.mcp.client.core",
    "MCPConfig": "lexigram.ai.mcp.config",
    "MCPError": "lexigram.ai.mcp.exceptions",
    "MCPInitializationError": "lexigram.ai.mcp.exceptions",
    "MCPMethodNotFoundError": "lexigram.ai.mcp.exceptions",
    "MCPModule": "lexigram.ai.mcp.module",
    "MCPPromptError": "lexigram.ai.mcp.exceptions",
    "MCPProtocolError": "lexigram.ai.mcp.exceptions",
    "MCPProvider": "lexigram.ai.mcp.di.provider",
    "MCPResourceError": "lexigram.ai.mcp.exceptions",
    "MCPServer": "lexigram.ai.mcp.server",
    "MCPToolCallError": "lexigram.ai.mcp.exceptions",
    "MCPTransportError": "lexigram.ai.mcp.exceptions",
    # Protocols
    "MCPToolProviderProtocol": "lexigram.ai.mcp.protocols",
    "MCPResourceProviderProtocol": "lexigram.ai.mcp.protocols",
    "MCPPromptProviderProtocol": "lexigram.ai.mcp.protocols",
    "MCPTransportProtocol": "lexigram.ai.mcp.protocols",
    "MCPServerProtocol": "lexigram.ai.mcp.protocols",
    "MCPToolHandlerProtocol": "lexigram.ai.mcp.protocols",
    "MCPResourceHandlerProtocol": "lexigram.ai.mcp.protocols",
    "MCPPromptHandlerProtocol": "lexigram.ai.mcp.protocols",
    "PromptHandler": "lexigram.ai.mcp.server.handlers",
    "ResourceHandler": "lexigram.ai.mcp.server.handlers",
    "SSETransport": "lexigram.ai.mcp.transport",
    "SSEClientTransport": "lexigram.ai.mcp.client.core",
    "StdioClientTransport": "lexigram.ai.mcp.client.core",
    "StdioTransport": "lexigram.ai.mcp.transport",
    "ToolHandler": "lexigram.ai.mcp.server.handlers",
    "ToolRegistryAdapter": "lexigram.ai.mcp.adapters",
    "prompt": "lexigram.ai.mcp.decorators",
    "resource": "lexigram.ai.mcp.decorators",
    "tool": "lexigram.ai.mcp.decorators",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib as _importlib

        module = _importlib.import_module(_LAZY_IMPORTS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = [
    "AbstractTransport",
    "ControllerPromptProvider",
    "ControllerResourceProvider",
    "ControllerToolProvider",
    "MCPClient",
    "MCPClientModule",
    "MCPClientProvider",
    "MCPClientRegistry",
    "MCPClientTransport",
    "MCPConfig",
    "MCPConnection",
    "MCPController",
    "MCPError",
    "MCPInitializationError",
    "MCPInitializeResult",
    "MCPJSONRPCRequest",
    "MCPJSONRPCResponse",
    "MCPMethodNotFoundError",
    "MCPModule",
    "MCPPrompt",
    "MCPPromptError",
    "MCPPromptHandlerProtocol",
    "MCPPromptMessage",
    "MCPPromptProviderProtocol",
    "MCPProtocolError",
    "MCPProvider",
    "MCPResource",
    "MCPResourceContent",
    "MCPResourceError",
    "MCPResourceHandlerProtocol",
    "MCPResourceProviderProtocol",
    "MCPServer",
    "MCPServerCapabilities",
    "MCPServerInfo",
    "MCPServerProtocol",
    "MCPServerStartedHook",
    "MCPServerStoppedHook",
    "MCPToolCallError",
    "MCPToolDefinition",
    "MCPToolHandlerProtocol",
    "MCPToolInvokedHook",
    "MCPToolProviderProtocol",
    "MCPTransportProtocol",
    "ModulePromptProvider",
    "ModuleResourceProvider",
    "ModuleToolProvider",
    "PromptHandler",
    "ResourceHandler",
    "SSEClientTransport",
    "SSETransport",
    "ServiceToolProvider",
    "StdioClientTransport",
    "StdioTransport",
    "ToolHandler",
    "ToolRegistryAdapter",
    "prompt",
    "resource",
    "tool",
]
