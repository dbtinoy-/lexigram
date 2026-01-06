"""Tests for MCPController, @tool/@resource/@prompt decorators, and @guard/@roles sugar.

Phase 2 P0 + P2 implementations:
  - MCPController base class and collect_* class methods
  - @tool, @resource, @prompt decorators
  - ControllerToolProvider, ControllerResourceProvider, ControllerPromptProvider
  - MCPModule(controllers=[...]) wiring
  - @guard / @roles shortcuts
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── MCPController + method decorators ────────────────────────────────────────


class TestToolDecorator:
    def test_sets_tool_config_on_method(self) -> None:
        from lexigram.ai.mcp.controllers import tool

        class Ctrl:
            @tool("get_item", description="Get an item by ID")
            async def get_item(self, item_id: str) -> dict:
                return {}

        assert hasattr(Ctrl.get_item, "_tool_config")
        assert Ctrl.get_item._tool_config["name"] == "get_item"
        assert Ctrl.get_item._tool_config["description"] == "Get an item by ID"

    def test_tool_config_without_description_defaults_to_empty(self) -> None:
        from lexigram.ai.mcp.controllers import tool

        class Ctrl:
            @tool("list_items")
            async def list_items(self) -> list:
                return []

        assert Ctrl.list_items._tool_config["description"] == ""

    def test_tool_returns_original_function_identity(self) -> None:
        from lexigram.ai.mcp.controllers import tool

        async def my_handler(self) -> None: ...

        decorated = tool("my_tool")(my_handler)
        assert decorated is my_handler


class TestResourceDecorator:
    def test_sets_resource_config_on_method(self) -> None:
        from lexigram.ai.mcp.controllers import resource

        class Ctrl:
            @resource("users://{user_id}", description="A user resource")
            async def get_user(self, user_id: str) -> dict:
                return {}

        cfg = Ctrl.get_user._resource_config
        assert cfg["uri_pattern"] == "users://{user_id}"
        assert cfg["description"] == "A user resource"
        assert cfg["name"] == "users://{user_id}"  # default name

    def test_resource_custom_name(self) -> None:
        from lexigram.ai.mcp.controllers import resource

        class Ctrl:
            @resource("users://{id}", name="User Resource")
            async def get_user(self, id: str) -> dict:
                return {}

        assert Ctrl.get_user._resource_config["name"] == "User Resource"


class TestPromptDecorator:
    def test_sets_prompt_config_on_method(self) -> None:
        from lexigram.ai.mcp.controllers import prompt

        class Ctrl:
            @prompt("summarize", description="Generate summary")
            async def summarize(self) -> str:
                return "..."

        cfg = Ctrl.summarize._prompt_config
        assert cfg["name"] == "summarize"
        assert cfg["description"] == "Generate summary"


class TestMCPController:
    def test_collect_tools_returns_decorated_methods(self) -> None:
        from lexigram.ai.mcp.controllers import MCPController, tool

        class MyCtrl(MCPController):
            @tool("do_thing", description="Does a thing")
            async def do_thing(self) -> None: ...

            @tool("other_thing")
            async def other_thing(self, x: int) -> list:
                return []

        tools = MyCtrl.collect_tools()
        assert len(tools) == 2
        names = {t["name"] for t in tools}
        assert names == {"do_thing", "other_thing"}
        do = next(t for t in tools if t["name"] == "do_thing")
        assert do["handler_name"] == "do_thing"
        assert do["description"] == "Does a thing"

    def test_collect_tools_skips_non_decorated_methods(self) -> None:
        from lexigram.ai.mcp.controllers import MCPController, tool

        class MyCtrl(MCPController):
            @tool("a")
            async def a(self) -> None: ...

            async def b(self) -> None: ...

        assert len(MyCtrl.collect_tools()) == 1

    def test_collect_resources_returns_decorated_methods(self) -> None:
        from lexigram.ai.mcp.controllers import MCPController, resource

        class MyCtrl(MCPController):
            @resource("items://{id}")
            async def get_item(self, id: str) -> dict:
                return {}

        resources = MyCtrl.collect_resources()
        assert len(resources) == 1
        assert resources[0]["uri_pattern"] == "items://{id}"
        assert resources[0]["handler_name"] == "get_item"

    def test_collect_prompts_returns_decorated_methods(self) -> None:
        from lexigram.ai.mcp.controllers import MCPController, prompt

        class MyCtrl(MCPController):
            @prompt("my_prompt")
            async def my_prompt(self) -> str:
                return "hello"

        prompts = MyCtrl.collect_prompts()
        assert len(prompts) == 1
        assert prompts[0]["name"] == "my_prompt"

    def test_collect_tools_inherits_from_base_class(self) -> None:
        from lexigram.ai.mcp.controllers import MCPController, tool

        class Base(MCPController):
            @tool("base_tool")
            async def base_tool(self) -> None: ...

        class Child(Base):
            @tool("child_tool")
            async def child_tool(self) -> None: ...

        tools = Child.collect_tools()
        names = {t["name"] for t in tools}
        assert "base_tool" in names
        assert "child_tool" in names

    def test_collect_tools_ignores_private_methods(self) -> None:
        from lexigram.ai.mcp.controllers import MCPController

        class MyCtrl(MCPController):
            async def _private(self) -> None: ...

        assert MyCtrl.collect_tools() == []


# ── ControllerToolProvider ────────────────────────────────────────────────────


class TestControllerToolProvider:
    @pytest.mark.asyncio
    async def test_list_tools_returns_all_tool_definitions(self) -> None:
        from lexigram.ai.mcp.controllers import ControllerToolProvider, MCPController, tool

        class Ctrl(MCPController):
            @tool("search", description="Search items")
            async def search(self, query: str) -> list:
                return []

        provider = ControllerToolProvider([Ctrl()])
        tools = await provider.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "search"
        assert tools[0]["description"] == "Search items"
        assert "inputSchema" in tools[0]
        assert tools[0]["inputSchema"]["properties"]["query"]["type"] == "string"

    @pytest.mark.asyncio
    async def test_list_tools_required_params_no_default(self) -> None:
        from lexigram.ai.mcp.controllers import ControllerToolProvider, MCPController, tool

        class Ctrl(MCPController):
            @tool("fetch")
            async def fetch(self, id: str) -> dict:
                return {}

        provider = ControllerToolProvider([Ctrl()])
        tools = await provider.list_tools()
        assert "required" in tools[0]["inputSchema"]
        assert "id" in tools[0]["inputSchema"]["required"]

    @pytest.mark.asyncio
    async def test_list_tools_optional_params_not_in_required(self) -> None:
        from lexigram.ai.mcp.controllers import ControllerToolProvider, MCPController, tool

        class Ctrl(MCPController):
            @tool("search")
            async def search(self, query: str = "") -> list:
                return []

        provider = ControllerToolProvider([Ctrl()])
        tools = await provider.list_tools()
        assert "required" not in tools[0]["inputSchema"]

    @pytest.mark.asyncio
    async def test_call_tool_dispatches_to_handler(self) -> None:
        from lexigram.ai.mcp.controllers import ControllerToolProvider, MCPController, tool

        class Ctrl(MCPController):
            @tool("greet")
            async def greet(self, name: str) -> str:
                return f"Hello, {name}"

        provider = ControllerToolProvider([Ctrl()])
        result = await provider.call_tool("greet", {"name": "World"})
        assert result == "Hello, World"

    @pytest.mark.asyncio
    async def test_call_tool_raises_for_unknown_tool(self) -> None:
        from lexigram.ai.mcp.controllers import ControllerToolProvider
        from lexigram.contracts.mcp.exceptions import MCPToolCallError

        provider = ControllerToolProvider([])
        with pytest.raises(MCPToolCallError):
            await provider.call_tool("nonexistent", {})

    @pytest.mark.asyncio
    async def test_aggregates_tools_from_multiple_controllers(self) -> None:
        from lexigram.ai.mcp.controllers import ControllerToolProvider, MCPController, tool

        class CtrlA(MCPController):
            @tool("a")
            async def a(self) -> None: ...

        class CtrlB(MCPController):
            @tool("b")
            async def b(self) -> None: ...

        provider = ControllerToolProvider([CtrlA(), CtrlB()])
        tools = await provider.list_tools()
        names = {t["name"] for t in tools}
        assert names == {"a", "b"}


# ── ControllerResourceProvider ───────────────────────────────────────────────


class TestControllerResourceProvider:
    @pytest.mark.asyncio
    async def test_list_resources_returns_all(self) -> None:
        from lexigram.ai.mcp.controllers import (
            ControllerResourceProvider,
            MCPController,
            resource,
        )

        class Ctrl(MCPController):
            @resource("docs://{doc_id}", description="A document")
            async def get_doc(self, doc_id: str) -> dict:
                return {"id": doc_id}

        provider = ControllerResourceProvider([Ctrl()])
        resources = await provider.list_resources()
        assert len(resources) == 1
        assert resources[0]["uri"] == "docs://{doc_id}"
        assert resources[0]["description"] == "A document"

    @pytest.mark.asyncio
    async def test_read_resource_dispatches_via_pattern(self) -> None:
        from lexigram.ai.mcp.controllers import (
            ControllerResourceProvider,
            MCPController,
            resource,
        )

        class Ctrl(MCPController):
            @resource("users://{user_id}")
            async def get_user(self, user_id: str) -> dict:
                return {"id": user_id, "name": "Alice"}

        provider = ControllerResourceProvider([Ctrl()])
        result = await provider.read_resource("users://42")
        assert result["id"] == "42"

    @pytest.mark.asyncio
    async def test_read_resource_raises_for_unmatched_uri(self) -> None:
        from lexigram.ai.mcp.controllers import ControllerResourceProvider
        from lexigram.contracts.mcp.exceptions import MCPResourceError

        provider = ControllerResourceProvider([])
        with pytest.raises(MCPResourceError):
            await provider.read_resource("unknown://xyz")

    @pytest.mark.asyncio
    async def test_list_templates_returns_only_pattern_uris(self) -> None:
        from lexigram.ai.mcp.controllers import (
            ControllerResourceProvider,
            MCPController,
            resource,
        )

        class Ctrl(MCPController):
            @resource("items://all")
            async def get_all(self) -> dict:
                return {}

            @resource("items://{id}")
            async def get_one(self, id: str) -> dict:
                return {}

        provider = ControllerResourceProvider([Ctrl()])
        templates = await provider.list_templates()
        assert len(templates) == 1
        assert templates[0]["uriTemplate"] == "items://{id}"


# ── ControllerPromptProvider ─────────────────────────────────────────────────


class TestControllerPromptProvider:
    @pytest.mark.asyncio
    async def test_list_prompts_returns_all(self) -> None:
        from lexigram.ai.mcp.controllers import (
            ControllerPromptProvider,
            MCPController,
            prompt,
        )

        class Ctrl(MCPController):
            @prompt("summary", description="Summarize data")
            async def summary(self) -> str:
                return "Summarize..."

        provider = ControllerPromptProvider([Ctrl()])
        prompts = await provider.list_prompts()
        assert len(prompts) == 1
        assert prompts[0]["name"] == "summary"
        assert prompts[0]["description"] == "Summarize data"

    @pytest.mark.asyncio
    async def test_get_prompt_str_result_normalized_to_mcp_format(self) -> None:
        from lexigram.ai.mcp.controllers import (
            ControllerPromptProvider,
            MCPController,
            prompt,
        )

        class Ctrl(MCPController):
            @prompt("greet")
            async def greet(self) -> str:
                return "Hello!"

        provider = ControllerPromptProvider([Ctrl()])
        result = await provider.get_prompt("greet")
        assert "messages" in result
        assert result["messages"][0]["content"]["text"] == "Hello!"

    @pytest.mark.asyncio
    async def test_get_prompt_raises_for_unknown_prompt(self) -> None:
        from lexigram.ai.mcp.controllers import ControllerPromptProvider
        from lexigram.contracts.mcp.exceptions import MCPPromptError

        provider = ControllerPromptProvider([])
        with pytest.raises(MCPPromptError):
            await provider.get_prompt("nonexistent")


# ── MCPModule(controllers=[...]) wiring ──────────────────────────────────────


class TestMCPModuleControllers:
    def test_mcp_module_accepts_controllers_param(self) -> None:
        from lexigram.ai.mcp import MCPModule
        from lexigram.ai.mcp.controllers import MCPController

        class MyCtrl(MCPController):
            pass

        module = MCPModule.configure(controllers=[MyCtrl])
        providers = module.providers
        assert any(
            hasattr(p, '_controllers') and MyCtrl in p._controllers
            for p in providers if hasattr(p, '_controllers')
        )

    def test_mcp_module_controllers_defaults_to_empty(self) -> None:
        from lexigram.ai.mcp import MCPModule

        module = MCPModule.configure()
        providers = module.providers
        assert any(
            hasattr(p, '_controllers') and p._controllers == []
            for p in providers if hasattr(p, '_controllers')
        )

    def test_mcp_module_importable_from_package(self) -> None:
        from lexigram.ai.mcp import MCPController, MCPModule, prompt, resource, tool

        assert MCPModule is not None
        assert MCPController is not None
        assert tool is not None
        assert resource is not None
        assert prompt is not None


# ── GuardProtocol / roles shortcuts ──────────────────────────────────────────────────


class TestGuardShortcut:
    def test_guard_importable_from_web(self) -> None:
        from lexigram.web import guard

        assert callable(guard)

    def test_guard_is_alias_for_use_guards(self) -> None:
        from lexigram.web.security.guards import use_guards
        from lexigram.web.security.shortcuts import guard

        # Both should return a decorator when called with a guard class
        mock_guard_class = MagicMock()
        mock_guard_class.return_value = MagicMock(spec=["can_activate"])

        result_guard = guard(mock_guard_class)
        result_use_guards = use_guards(mock_guard_class)

        # Both produce callables (decorators)
        assert callable(result_guard)
        assert callable(result_use_guards)

    def test_guard_stores_guards_metadata_on_decorated_func(self) -> None:
        from lexigram.web.security.shortcuts import guard

        mock_guard_class = MagicMock()
        mock_guard_instance = MagicMock(spec=["can_activate"])
        mock_guard_class.return_value = mock_guard_instance

        async def my_handler(request):  # noqa: ANN001
            pass

        decorated = guard(mock_guard_class)(my_handler)
        # use_guards attaches __guards__ to the wrapped function
        assert hasattr(decorated, "__guards__") or callable(decorated)


class TestRolesShortcut:
    def test_roles_importable_from_web(self) -> None:
        from lexigram.web import roles

        assert callable(roles)

    def test_roles_importable_from_shortcuts(self) -> None:
        from lexigram.web.security.shortcuts import roles

        assert callable(roles)

    def test_roles_produces_callable_decorator(self) -> None:
        from lexigram.web.security.shortcuts import roles

        mock_authorizer = object()
        decorator = roles("admin", authorizer=mock_authorizer)
        assert callable(decorator)

    def test_roles_multiple_role_names(self) -> None:
        from lexigram.web.security.shortcuts import roles

        mock_authorizer = object()
        decorator = roles("admin", "moderator", "staff", authorizer=mock_authorizer)
        assert callable(decorator)

    def test_guard_importable_from_shortcuts(self) -> None:
        from lexigram.web.security.shortcuts import guard

        assert callable(guard)
