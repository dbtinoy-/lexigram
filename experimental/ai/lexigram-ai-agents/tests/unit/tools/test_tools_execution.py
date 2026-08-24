from __future__ import annotations

import pytest

from lexigram.ai.agents.tools import tool, ToolRegistryImpl
from lexigram.ai.agents.exceptions import ToolAccessDeniedError, ToolExecutionError, ToolNotFoundError


class _FakeModuleNode:
    def __init__(self, imports: list[type] | None = None, is_global: bool = False) -> None:
        self.imports = imports or []
        self.is_global = is_global


class _FakeModuleGraph:
    def __init__(self, mapping: dict[type, _FakeModuleNode]) -> None:
        self._mapping = mapping

    def get_module(self, module_class: type) -> _FakeModuleNode | None:
        return self._mapping.get(module_class)


class _BrokenModuleGraph:
    def get_module(self, module_class: type) -> None:
        raise RuntimeError("graph lookup failed")


class TestToolRegistryVisibilityAndErrors:
    @pytest.mark.asyncio
    async def test_execute_returns_tool_not_found_error(self) -> None:
        registry = ToolRegistryImpl()

        result = await registry.execute("missing_tool")

        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, ToolNotFoundError)
        assert error.details["tool"] == "missing_tool"

    @pytest.mark.asyncio
    async def test_execute_returns_access_denied_when_tool_not_visible(self) -> None:
        class CallerModule:
            pass

        class ToolModule:
            pass

        @tool
        async def hidden_tool() -> str:
            return "hidden"

        registry = ToolRegistryImpl()
        registry.register(hidden_tool, module_class=ToolModule)
        registry.set_caller_module(CallerModule)
        registry.set_module_graph(
            _FakeModuleGraph(
                {
                    CallerModule: _FakeModuleNode(imports=[]),
                    ToolModule: _FakeModuleNode(is_global=False),
                }
            )
        )

        result = await registry.execute("hidden_tool")

        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, ToolAccessDeniedError)
        assert error.details["tool"] == "hidden_tool"
        assert error.details["agent_module"] == "CallerModule"
        assert error.details["tool_module"] == "ToolModule"

    @pytest.mark.asyncio
    async def test_execute_wraps_tool_exception_in_tool_execution_error(self) -> None:
        @tool
        async def failing_tool(attempt: int) -> str:
            raise ValueError("boom")

        registry = ToolRegistryImpl()
        registry.register(failing_tool)

        result = await registry.execute("failing_tool", attempt=1)

        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, ToolExecutionError)
        assert isinstance(error.cause, ValueError)
        assert error.details["tool"] == "failing_tool"
        assert error.details["arguments"] == {"attempt": 1}

    @pytest.mark.asyncio
    async def test_visibility_check_denies_access_when_graph_lookup_raises(self) -> None:
        class CallerModule:
            pass

        class ToolModule:
            pass

        @tool
        async def unstable_graph_tool() -> str:
            return "ok"

        registry = ToolRegistryImpl()
        registry.register(unstable_graph_tool, module_class=ToolModule)
        registry.set_caller_module(CallerModule)
        registry.set_module_graph(_BrokenModuleGraph())

        result = await registry.execute("unstable_graph_tool")

        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, ToolAccessDeniedError)
        assert error.details["tool"] == "unstable_graph_tool"
        assert error.details["agent_module"] == "CallerModule"
        assert error.details["tool_module"] == "ToolModule"

    def test_repr_shows_visible_count_and_clear_resets_registry(self) -> None:
        class CallerModule:
            pass

        class ImportedToolModule:
            pass

        class HiddenToolModule:
            pass

        @tool
        async def visible_tool() -> str:
            return "visible"

        @tool
        async def hidden_tool() -> str:
            return "hidden"

        registry = ToolRegistryImpl()
        registry.register(visible_tool, module_class=ImportedToolModule)
        registry.register(hidden_tool, module_class=HiddenToolModule)
        registry.set_caller_module(CallerModule)
        registry.set_module_graph(
            _FakeModuleGraph(
                {
                    CallerModule: _FakeModuleNode(imports=[ImportedToolModule]),
                    ImportedToolModule: _FakeModuleNode(is_global=False),
                    HiddenToolModule: _FakeModuleNode(is_global=False),
                }
            )
        )

        assert repr(registry) == "ToolRegistry(tools=2, visible=1)"

        registry.clear()

        assert len(registry.list_tools()) == 0
        assert repr(registry) == "ToolRegistry(tools=0)"
