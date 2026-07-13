"""Tests for script-mode MCP providers (ModuleToolProvider, ModuleResourceProvider,
ModulePromptProvider) and the CLI helper functions _load_script_module,
_build_script_server, _is_script_target.
"""

from __future__ import annotations

import types
from typing import Any

import pytest

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_module(**funcs: Any) -> types.ModuleType:
    """Build a throwaway module populated with the given attributes."""
    mod = types.ModuleType("_test_script")
    for name, obj in funcs.items():
        setattr(mod, name, obj)
    return mod


# ═════════════════════════════════════════════════════════════════════════════
# ModuleToolProvider
# ═════════════════════════════════════════════════════════════════════════════


class TestModuleToolProvider:
    @pytest.mark.asyncio
    async def test_list_tools_returns_decorated_funcs(self) -> None:
        from lexigram.ai.mcp.controllers import ModuleToolProvider, tool

        @tool("search", description="Search something")
        async def search(query: str) -> list[dict]:
            return []

        provider = ModuleToolProvider([search])
        tools = await provider.list_tools()

        assert len(tools) == 1
        assert tools[0]["name"] == "search"
        assert tools[0]["description"] == "Search something"

    @pytest.mark.asyncio
    async def test_from_module_discovers_all_tools(self) -> None:
        from lexigram.ai.mcp.controllers import ModuleToolProvider, tool

        @tool("tool_a")
        async def tool_a() -> dict:
            return {}

        @tool("tool_b")
        async def tool_b(name: str) -> dict:
            return {"name": name}

        def not_a_tool() -> None:
            pass

        mod = _make_module(tool_a=tool_a, tool_b=tool_b, not_a_tool=not_a_tool)
        provider = ModuleToolProvider.from_module(mod)
        tools = await provider.list_tools()

        names = {t["name"] for t in tools}
        assert names == {"tool_a", "tool_b"}

    @pytest.mark.asyncio
    async def test_call_tool_invokes_function(self) -> None:
        from lexigram.ai.mcp.controllers import ModuleToolProvider, tool

        @tool("greet")
        async def greet(name: str = "World") -> str:
            return f"Hello, {name}!"

        provider = ModuleToolProvider([greet])
        result = await provider.call_tool("greet", {"name": "Alice"})

        assert result == "Hello, Alice!"

    @pytest.mark.asyncio
    async def test_call_tool_raises_for_unknown_tool(self) -> None:
        from lexigram.ai.mcp.controllers import ModuleToolProvider
        from lexigram.contracts.mcp.exceptions import MCPToolCallError

        provider = ModuleToolProvider([])
        with pytest.raises(MCPToolCallError):
            await provider.call_tool("nonexistent", {})

    @pytest.mark.asyncio
    async def test_input_schema_excludes_self(self) -> None:
        """Standalone functions don't have self — schema should not include it."""
        from lexigram.ai.mcp.controllers import ModuleToolProvider, tool

        @tool("fn")
        async def fn(x: int, y: str = "default") -> dict:
            return {}

        provider = ModuleToolProvider([fn])
        tools = await provider.list_tools()

        schema = tools[0]["inputSchema"]
        assert "self" not in schema["properties"]
        assert "x" in schema["properties"]
        assert "y" in schema["properties"]
        assert schema.get("required") == ["x"]


# ═════════════════════════════════════════════════════════════════════════════
# ModuleResourceProvider
# ═════════════════════════════════════════════════════════════════════════════


class TestModuleResourceProvider:
    @pytest.mark.asyncio
    async def test_from_module_discovers_resources(self) -> None:
        from lexigram.ai.mcp.controllers import ModuleResourceProvider, resource

        @resource("users://{uid}", description="A user")
        async def get_user(uid: str) -> dict:
            return {"id": uid}

        mod = _make_module(get_user=get_user)
        provider = ModuleResourceProvider.from_module(mod)
        resources = await provider.list_resources()

        assert len(resources) == 1
        assert resources[0]["uri"] == "users://{uid}"

    @pytest.mark.asyncio
    async def test_read_resource_dispatches_via_pattern(self) -> None:
        from lexigram.ai.mcp.controllers import ModuleResourceProvider, resource

        @resource("items://{item_id}")
        async def get_item(item_id: str) -> dict:
            return {"id": item_id}

        provider = ModuleResourceProvider([get_item])
        result = await provider.read_resource("items://99")

        assert result["id"] == "99"

    @pytest.mark.asyncio
    async def test_list_templates_only_returns_patterns(self) -> None:
        from lexigram.ai.mcp.controllers import ModuleResourceProvider, resource

        @resource("static://foo")
        async def static() -> str:
            return "static"

        @resource("dynamic://{id}")
        async def dynamic(id: str) -> str:
            return id

        provider = ModuleResourceProvider([static, dynamic])
        templates = await provider.list_templates()

        uris = [t["uriTemplate"] for t in templates]
        assert "dynamic://{id}" in uris
        assert "static://foo" not in uris


# ═════════════════════════════════════════════════════════════════════════════
# ModulePromptProvider
# ═════════════════════════════════════════════════════════════════════════════


class TestModulePromptProvider:
    @pytest.mark.asyncio
    async def test_from_module_discovers_prompts(self) -> None:
        from lexigram.ai.mcp.controllers import ModulePromptProvider, prompt

        @prompt("analyze", description="Analyze data")
        async def analyze() -> str:
            return "Please analyze..."

        mod = _make_module(analyze=analyze)
        provider = ModulePromptProvider.from_module(mod)
        prompts = await provider.list_prompts()

        assert len(prompts) == 1
        assert prompts[0]["name"] == "analyze"

    @pytest.mark.asyncio
    async def test_get_prompt_normalizes_str(self) -> None:
        from lexigram.ai.mcp.controllers import ModulePromptProvider, prompt

        @prompt("hello")
        async def hello() -> str:
            return "Hello, world!"

        provider = ModulePromptProvider([hello])
        result = await provider.get_prompt("hello")

        assert "messages" in result
        assert result["messages"][0]["content"]["text"] == "Hello, world!"

    @pytest.mark.asyncio
    async def test_get_prompt_raises_for_unknown(self) -> None:
        from lexigram.ai.mcp.controllers import ModulePromptProvider
        from lexigram.contracts.mcp.exceptions import MCPPromptError

        provider = ModulePromptProvider([])
        with pytest.raises(MCPPromptError):
            await provider.get_prompt("unknown")


# ═════════════════════════════════════════════════════════════════════════════
# _is_script_target and _build_script_server (CLI helpers)
# ═════════════════════════════════════════════════════════════════════════════


class TestIsScriptTarget:
    def test_py_file_is_always_script(self) -> None:
        from lexigram.ai.mcp.cli.commands import _is_script_target

        assert _is_script_target("tools.py") is True
        assert _is_script_target("./my_tools.py") is True
        assert _is_script_target("/abs/path/tools.py") is True

    def test_module_colon_attr_is_not_script(self) -> None:
        from lexigram.ai.mcp.cli.commands import _is_script_target

        assert _is_script_target("my_app.app:create_app") is False
        assert _is_script_target("app:app") is False

    def test_dotted_name_without_colon_is_script_when_no_factory(self) -> None:
        from lexigram.ai.mcp.cli.commands import _is_script_target

        # Does not point to a real file, so no factory detected → script mode
        assert _is_script_target("my_app.mcp_tools") is True


class TestBuildScriptServer:
    @pytest.mark.asyncio
    async def test_build_script_server_from_module(self) -> None:
        from lexigram.ai.mcp.cli.commands import _build_script_server
        from lexigram.ai.mcp.controllers import tool

        @tool("ping")
        async def ping() -> str:
            return "pong"

        mod = _make_module(ping=ping)
        server = _build_script_server(mod)

        # Server should be an MCPServer instance
        from lexigram.ai.mcp.server.core import MCPServer

        assert isinstance(server, MCPServer)

    @pytest.mark.asyncio
    async def test_script_server_uses_module_name(self) -> None:
        from lexigram.ai.mcp.cli.commands import _build_script_server
        from lexigram.ai.mcp.server.core import MCPServer

        mod = types.ModuleType("my_tools")
        mod.__mcp_name__ = "custom-server"  # type: ignore[attr-defined]
        server = _build_script_server(mod)

        assert isinstance(server, MCPServer)
        assert server._name == "custom-server"


class TestLoadScriptModule:
    def test_load_by_dotted_name(self) -> None:
        import sys

        from lexigram.ai.mcp.cli.commands import _load_script_module

        # Use a real importable module from stdlib
        mod = _load_script_module("json")
        assert mod is sys.modules["json"]

    def test_load_from_file(self, tmp_path) -> None:
        from lexigram.ai.mcp.cli.commands import _load_script_module

        script = tmp_path / "my_tools.py"
        script.write_text(
            "from lexigram.ai.mcp.controllers import tool\n\n"
            "@tool('double')\n"
            "async def double(x: int) -> int:\n"
            "    return x * 2\n"
        )
        mod = _load_script_module(str(script))
        assert hasattr(mod, "double")
        assert hasattr(mod.double, "_tool_config")
        assert mod.double._tool_config["name"] == "double"
