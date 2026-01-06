"""Tests for component registry."""

import pytest

from lexigram.admin.services.component_registry import (
    ComponentMetadata,
    ComponentRegistry,
    get_component_registry,
    register_component,
)


# Test components
class MockButton:
    """Test button component."""

    def __init__(self, text: str = "Click"):
        self.text = text


class MockCard:
    """Test card component."""

    def __init__(self, title: str = "Card"):
        self.title = title


class TestTable:
    """Test table component."""

    pass


@pytest.fixture
def registry():
    """Create fresh registry for each test."""
    reg = ComponentRegistry()
    yield reg
    reg.clear()


def test_register_component(registry):
    """Test direct component registration."""
    registry.register("button", MockButton, version="1.0.0", description="A button")

    assert registry.has("button")
    Button = registry.get("button")
    assert Button is MockButton

    metadata = registry.get_metadata("button")
    assert metadata.name == "button"
    assert metadata.version == "1.0.0"
    assert metadata.description == "A button"
    assert metadata.lazy is False


def test_register_with_tags(registry):
    """Test registration with tags."""
    registry.register("button", MockButton, tags=["form", "ui", "input"])

    metadata = registry.get_metadata("button")
    assert "form" in metadata.tags
    assert "ui" in metadata.tags


def test_register_with_aliases(registry):
    """Test registration with aliases."""
    registry.register("button", MockButton, aliases=["btn", "submit_button"])

    # Access via alias
    Button = registry.get("btn")
    assert Button is MockButton

    Button = registry.get("submit_button")
    assert Button is MockButton


def test_register_duplicate_raises_error(registry):
    """Test that registering duplicate name raises error."""
    registry.register("button", MockButton)

    with pytest.raises(ValueError, match="already registered"):
        registry.register("button", MockCard)


def test_register_lazy(registry):
    """Test lazy component registration."""
    registry.register_lazy(
        "button",
        f"{__name__}.MockButton",
        version="1.0.0",
    )

    assert registry.has("button")
    metadata = registry.get_metadata("button")
    assert metadata.lazy is True

    # Component should load on access
    ButtonClass = registry.get("button")
    instance = ButtonClass(text="Test")
    assert instance.text == "Test"


def test_get_nonexistent_raises_error(registry):
    """Test getting nonexistent component raises error."""
    with pytest.raises(KeyError, match="not found"):
        registry.get("nonexistent")


def test_has_component(registry):
    """Test checking component existence."""
    assert not registry.has("button")

    registry.register("button", MockButton)

    assert registry.has("button")
    assert registry.has("btn") is False  # Alias not registered


def test_deprecate_component(registry):
    """Test deprecating a component."""
    registry.register("button", MockButton)
    registry.deprecate("button", replacement="new_button")

    metadata = registry.get_metadata("button")
    assert metadata.deprecated is True
    assert metadata.replacement == "new_button"

    # Getting deprecated component raises error
    with pytest.raises(ValueError, match="deprecated"):
        registry.get("button")


def test_deprecate_with_message(registry):
    """Test deprecating with custom message."""
    registry.register("button", MockButton)
    registry.deprecate("button", replacement="new_button", message="Use new API")

    with pytest.raises(ValueError, match="deprecated"):
        registry.get("button")


def test_list_components(registry):
    """Test listing all components."""
    registry.register("button", MockButton)
    registry.register("card", MockCard)
    registry.register("table", TestTable)

    components = registry.list_components()
    assert components == ["button", "card", "table"]


def test_list_components_with_tags(registry):
    """Test filtering components by tags."""
    registry.register("button", MockButton, tags=["form", "input"])
    registry.register("card", MockCard, tags=["layout"])
    registry.register("table", TestTable, tags=["data", "table"])

    # Filter by single tag
    components = registry.list_components(tags=["form"])
    assert components == ["button"]

    # Filter by multiple tags (any match)
    components = registry.list_components(tags=["layout", "data"])
    assert "card" in components
    assert "table" in components


def test_list_components_exclude_deprecated(registry):
    """Test that deprecated components are excluded by default."""
    registry.register("button", MockButton)
    registry.register("old_button", MockCard)
    registry.deprecate("old_button")

    components = registry.list_components()
    assert "button" in components
    assert "old_button" not in components

    # Include deprecated
    components = registry.list_components(include_deprecated=True)
    assert "old_button" in components


def test_get_version(registry):
    """Test getting component version."""
    registry.register("button", MockButton, version="1.2.3")

    version = registry.get_version("button")
    assert version == "1.2.3"


def test_check_version(registry):
    """Test version checking."""
    registry.register("button", MockButton, version="1.2.3")

    assert registry.check_version("button", "1.0.0") is True
    assert registry.check_version("button", "1.2.3") is True
    assert registry.check_version("button", "2.0.0") is False


def test_version_comparison(registry):
    """Test semantic version comparison."""
    assert registry._compare_versions("1.0.0", "1.0.0") == 0
    assert registry._compare_versions("1.2.3", "1.2.2") == 1
    assert registry._compare_versions("1.2.2", "1.2.3") == -1
    assert registry._compare_versions("2.0.0", "1.9.9") == 1
    assert registry._compare_versions("1.0", "1.0.0") == 0  # Padding


def test_clear_registry(registry):
    """Test clearing all components."""
    registry.register("button", MockButton)
    registry.register("card", MockCard)

    registry.clear()

    assert not registry.has("button")
    assert not registry.has("card")
    assert registry.list_components() == []


def test_export_manifest(registry):
    """Test exporting registry manifest."""
    registry.register(
        "button", MockButton, version="1.0.0", description="A button", tags=["ui"],
    )
    registry.register("card", MockCard, aliases=["panel"])

    manifest = registry.export_manifest()

    assert "components" in manifest
    assert "aliases" in manifest
    assert "button" in manifest["components"]
    assert manifest["components"]["button"]["version"] == "1.0.0"
    assert manifest["aliases"]["panel"] == "card"


def test_get_global_registry():
    """Test global registry singleton."""
    reg1 = get_component_registry()
    reg2 = get_component_registry()

    assert reg1 is reg2  # Same instance


def test_register_component_decorator():
    """Test @register_component decorator."""

    @register_component("test_button", version="1.0.0", description="Test")
    class DecoratedButton:
        pass

    registry = get_component_registry()

    assert registry.has("test_button")
    Button = registry.get("test_button")
    assert Button is DecoratedButton

    # Cleanup
    registry.clear()


def test_register_component_function():
    """Test register_component as function."""
    register_component("func_button", MockButton, version="1.0.0")

    registry = get_component_registry()
    assert registry.has("func_button")

    # Cleanup
    registry.clear()


def test_register_component_lazy_function():
    """Test register_component with lazy loading."""
    register_component(
        "lazy_button",
        import_path=f"{__name__}.MockButton",
        version="1.0.0",
    )

    registry = get_component_registry()
    assert registry.has("lazy_button")

    metadata = registry.get_metadata("lazy_button")
    assert metadata.lazy is True

    # Cleanup
    registry.clear()


def test_metadata_to_dict():
    """Test ComponentMetadata to_dict conversion."""
    metadata = ComponentMetadata(
        name="button",
        component_class=MockButton,
        version="1.0.0",
        description="A button",
        tags=["ui", "form"],
        lazy=False,
        deprecated=False,
    )

    data = metadata.to_dict()

    assert data["name"] == "button"
    assert data["version"] == "1.0.0"
    assert data["description"] == "A button"
    assert data["tags"] == ["ui", "form"]
    assert data["lazy"] is False
    assert data["deprecated"] is False
    assert "registered_at" in data


def test_lazy_loading_with_invalid_path(registry):
    """Test that lazy loading with invalid path raises on access."""
    registry.register_lazy("broken", "nonexistent.module.Class")

    # Registration should succeed
    assert registry.has("broken")

    # But accessing should fail
    with pytest.raises(ModuleNotFoundError):
        registry.get("broken")


def test_multiple_aliases_same_component(registry):
    """Test multiple aliases pointing to same component."""
    registry.register("button", MockButton, aliases=["btn", "submit", "action"])

    # All aliases resolve to same component
    assert registry.get("button") is MockButton
    assert registry.get("btn") is MockButton
    assert registry.get("submit") is MockButton
    assert registry.get("action") is MockButton


def test_deprecate_nonexistent_raises_error(registry):
    """Test deprecating nonexistent component raises error."""
    with pytest.raises(KeyError, match="not found"):
        registry.deprecate("nonexistent")


def test_component_metadata_defaults():
    """Test ComponentMetadata default values."""
    metadata = ComponentMetadata(name="test", component_class=MockButton)

    assert metadata.version == "1.0.0"
    assert metadata.description == ""
    assert metadata.tags == []
    assert metadata.lazy is False
    assert metadata.deprecated is False
    assert metadata.replacement is None
