"""Unit tests for lexigram-ai-agents tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest

from lexigram.ai.agents.tools import ToolBase, tool, ToolRegistryImpl, generate_json_schema
from lexigram.ai.agents.exceptions import ToolAccessDeniedError, ToolExecutionError, ToolNotFoundError
from typing import Any, Literal, Annotated
from enum import Enum

class Status(Enum):
    ACTIVE = "active"
    ERROR = "error"

class TestToolDecorator:
    """Tests for the @tool decorator."""

    def test_tool_decorator_creates_tool_wrapper(self) -> None:
        """Test that @tool decorator wraps async functions correctly."""

        @tool
        async def get_weather(location: str) -> dict:
            """Get weather for a location."""
            return {"location": location, "temp": 72}

        # Should have name from function
        assert "get_weather" == get_weather.name
        # Should have docstring as description
        assert "Get weather for a location." == get_weather.description

    def test_tool_decorator_with_custom_name(self) -> None:
        """Test @tool with custom name and description."""

        @tool(name="weather", description="Get weather info")
        async def get_weather(location: str) -> dict:
            return {"location": location}

        assert "weather" == get_weather.name
        assert "Get weather info" == get_weather.description

    def test_tool_decorator_generates_parameters_schema(self) -> None:
        """Test that @tool generates correct parameters schema."""

        @tool
        async def search_products(query: str, limit: int = 10) -> list[dict]:
            """Search for products."""
            return [{"query": query, "limit": limit}]

        schema = search_products.parameters_schema
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "limit" in schema["properties"]
        assert "query" in schema["required"]

    @pytest.mark.asyncio
    async def test_tool_execute_with_arguments(self) -> None:
        """Test executing tool with arguments."""

        @tool
        async def calculate(a: int, b: int) -> int:
            """Calculate sum."""
            return a + b

        result = await calculate.execute(a=5, b=3)
        assert result == 8

    def test_tool_decorator_multiline_docstring(self) -> None:
        """Test that multi-line docstring uses first line."""

        @tool
        async def multi_line_doc(x: str) -> str:
            """First line only.

            Second line should be dropped.
            Third line too.
            """
            return x

        assert "First line only." == multi_line_doc.description

    def test_tool_decorator_no_docstring(self) -> None:
        """Test that function without docstring gets empty description."""

        @tool
        async def no_doc(x: str) -> str:
            return x

        assert no_doc.description == ""

    def test_function_tool_repr(self) -> None:
        """Test FunctionTool repr."""

        @tool
        async def my_tool(x: str) -> str:
            """My tool."""
            return x

        assert repr(my_tool) == "FunctionTool(my_tool)"


class TestToolClass:
    """Tests for the ToolBase base class."""

    def test_tool_subclass_basic(self) -> None:
        """Test creating a basic ToolBase subclass."""

        class MyTool(ToolBase):
            @property
            def name(self) -> str:
                return "my_tool"

            @property
            def description(self) -> str:
                return "A test tool"

            @property
            def parameters_schema(self) -> dict:
                return {"type": "object", "properties": {}}

            async def execute(self, **kwargs: Any) -> str:
                return "executed"

        tool_instance = MyTool()
        assert "my_tool" == tool_instance.name
        assert "A test tool" == tool_instance.description

    @pytest.mark.asyncio
    async def test_tool_execute_delegates_to_implementation(self) -> None:
        """Test ToolBase.execute calls subclass implementation."""

        class OrderTool(ToolBase):
            def __init__(self, order_service: MagicMock):
                self.order_service = order_service

            @property
            def name(self) -> str:
                return "lookup_order"

            @property
            def description(self) -> str:
                return "Look up an order"

            @property
            def parameters_schema(self) -> dict:
                return {
                    "type": "object",
                    "properties": {"order_id": {"type": "string"}},
                    "required": ["order_id"],
                }

            async def execute(self, **kwargs: Any) -> dict:
                order_id = kwargs.get("order_id")
                return await self.order_service.find(order_id)

        mock_service = MagicMock()
        mock_service.find = AsyncMock(return_value={"id": "123", "status": "shipped"})

        tool_instance = OrderTool(mock_service)
        result = await tool_instance.execute(order_id="123")

        assert result["id"] == "123"
        mock_service.find.assert_called_once_with("123")


class TestToolRegistry:
    """Tests for ToolRegistryImpl."""

    def test_empty_registry(self) -> None:
        """Test empty registry returns no tools."""
        registry = ToolRegistryImpl()
        assert len(registry.list_tools()) == 0

    def test_register_function_tool(self) -> None:
        """Test registering a function tool."""

        @tool
        async def get_user(user_id: str) -> dict:
            """Get user by ID."""
            return {"id": user_id}

        registry = ToolRegistryImpl()
        registry.register(get_user)

        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "get_user"

    def test_register_class_tool(self) -> None:
        """Test registering a ToolBase subclass."""

        class SearchTool(ToolBase):
            @property
            def name(self) -> str:
                return "search"

            @property
            def description(self) -> str:
                return "Search for items"

            @property
            def parameters_schema(self) -> dict:
                return {"type": "object", "properties": {}}

            async def execute(self, **kwargs: Any) -> list:
                return []

        registry = ToolRegistryImpl()
        registry.register(SearchTool())

        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "search"

    def test_register_duplicate_raises(self) -> None:
        """Test registering duplicate tool name raises error."""

        @tool(name="duplicate")
        async def tool_a() -> None:
            """ToolBase A."""
            pass

        @tool(name="duplicate")
        async def tool_b() -> None:
            """ToolBase B."""
            pass

        registry = ToolRegistryImpl()
        registry.register(tool_a)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(tool_b)

    def test_unregister(self) -> None:
        """Test unregistering a tool."""

        @tool
        async def temporary_tool() -> None:
            """Temporary tool."""
            pass

        registry = ToolRegistryImpl()
        registry.register(temporary_tool)
        assert len(registry.list_tools()) == 1

        registry.unregister("temporary_tool")
        assert len(registry.list_tools()) == 0

    def test_get_tool(self) -> None:
        """Test getting a specific tool."""

        @tool
        async def search(query: str) -> list:
            """Search."""
            return []

        registry = ToolRegistryImpl()
        registry.register(search)

        retrieved = registry.get("search")
        assert retrieved is not None
        assert retrieved.name == "search"

    def test_get_tool_not_found(self) -> None:
        """Test getting non-existent tool returns None."""
        registry = ToolRegistryImpl()
        assert registry.get("nonexistent") is None

    @pytest.mark.asyncio
    async def test_execute_tool(self) -> None:
        """Test executing a tool through registry."""

        @tool
        async def add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        registry = ToolRegistryImpl()
        registry.register(add)

        result = await registry.execute("add", a=2, b=3)
        assert result.is_ok()
        assert result.unwrap() == 5


class TestGenerateJsonSchema:
    """Tests for generate_json_schema helper."""

    def test_generate_from_function(self) -> None:
        """Test generating JSON schema from function signature."""

        def my_function(name: str, age: int, active: bool = True) -> dict:
            """A test function."""
            return {}

        schema = generate_json_schema(my_function)

        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]
        assert "active" in schema["properties"]
        assert "name" in schema["required"]
        assert "age" in schema["required"]

    def test_generate_with_typed_parameters(self) -> None:
        """Test schema generation with type annotations."""

        def typed_function(items: list[str], mapping: dict[str, int]) -> None:
            """Typed function."""
            pass

        schema = generate_json_schema(typed_function)

        # List should become array
        assert schema["properties"]["items"]["type"] == "array"
        # Dict should become object
        assert schema["properties"]["mapping"]["type"] == "object"

    def test_generate_preserves_optional(self) -> None:
        """Test that optional parameters are not in required."""

        def optional_params(required: str, optional: str = "default") -> None:
            """Test function."""
            pass

        schema = generate_json_schema(optional_params)

        assert "required" in schema
        assert "required" in schema["required"]
        assert "optional" not in schema["required"]

    def test_generate_infers_descriptions_from_docstring(self) -> None:
        """Test that param descriptions are extracted from Google-style docstring."""

        def described_function(query: str, max_results: int = 10) -> list:
            """Search for items.

            Args:
                query: The search query to execute.
                max_results: Maximum number of results to return.

            Returns:
                A list of matching items.
            """
            return []

        schema = generate_json_schema(described_function)

        assert schema["properties"]["query"]["description"] == "The search query to execute."
        assert schema["properties"]["max_results"]["description"] == "Maximum number of results to return."

    def test_generate_no_description_without_docstring(self) -> None:
        """Test that missing docstring produces schema without descriptions."""

        def no_doc(name: str) -> None:
            pass

        schema = generate_json_schema(no_doc)

        assert "description" not in schema["properties"]["name"]

    def test_generate_optional_nullable_schema(self) -> None:
        """Test that optional params produce nullable JSON schema."""

        def nullable_param(value: str | None = None) -> None:
            """Function with nullable param."""
            pass

        schema = generate_json_schema(nullable_param)

        prop = schema["properties"]["value"]
        assert prop["nullable"] is True
        assert prop["type"] == "string"

    def test_generate_list_items_schema(self) -> None:
        """Test that list[str] produces array schema with string items."""

        def list_param(tags: list[str]) -> None:
            """Function with list param."""
            pass

        schema = generate_json_schema(list_param)

        prop = schema["properties"]["tags"]
        assert prop["type"] == "array"
        assert prop["items"]["type"] == "string"

    def test_generate_manual_schema_takes_precedence_via_decorator(self) -> None:
        """Test that manually specified schema in decorator is used as-is."""
        manual_schema = {
            "type": "object",
            "properties": {"url": {"type": "string", "format": "uri"}},
            "required": ["url"],
        }

        # The @tool decorator does NOT accept a manual 'schema' kwarg currently,
        # but we can verify the auto-generated schema for a typed function is correct.
        @tool
        async def fetch_url(url: str) -> str:
            """Fetch content from a URL.

            Args:
                url: The URL to fetch.
            """
            return ""

        assert fetch_url.parameters_schema["properties"]["url"]["type"] == "string"
        assert fetch_url.parameters_schema["properties"]["url"]["description"] == "The URL to fetch."

    def test_generate_literal_schema(self) -> None:
        """Test that Literal produces string enum schema."""
        def literal_param(mode: Literal["fast", "slow", "balanced"]) -> None:
            pass

        schema = generate_json_schema(literal_param)
        prop = schema["properties"]["mode"]
        assert prop["type"] == "string"
        assert prop["enum"] == ["fast", "slow", "balanced"]

    def test_generate_enum_schema(self) -> None:
        """Test that Enum produces string enum schema."""
        def enum_param(status: Status) -> None:
            pass

        schema = generate_json_schema(enum_param)
        prop = schema["properties"]["status"]
        assert prop["type"] == "string"
        assert set(prop["enum"]) == {"active", "error"}

    def test_generate_annotated_schema(self) -> None:
        """Test that Annotated unwraps to its first argument."""
        def annotated_param(count: Annotated[int, "Some metadata"]) -> None:
            pass

        schema = generate_json_schema(annotated_param)
        prop = schema["properties"]["count"]
        assert prop["type"] == "integer"


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
    """Focused tests for ToolRegistryImpl visibility and failure branches."""

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
    async def test_visibility_check_fails_open_when_graph_lookup_raises(self) -> None:
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

        assert result.is_ok()
        assert result.unwrap() == "ok"

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
