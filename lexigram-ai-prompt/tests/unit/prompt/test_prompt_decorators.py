"""Unit tests for prompt_template decorator."""

import pytest

from lexigram.ai.prompt.decorators import _PROMPT_REGISTRY, prompt_template


@pytest.fixture(autouse=True)
def clear_registry() -> None:
    """Clear the prompt registry before and after each test."""
    _PROMPT_REGISTRY.clear()
    yield
    _PROMPT_REGISTRY.clear()


class TestPromptTemplateDecorator:
    """Tests for the prompt_template decorator."""

    def test_decorator_registers_template(self) -> None:
        """Test that decorator registers template with name."""

        @prompt_template(name="test.template")
        class TestTemplate:
            pass

        registry_key = "test.template@1.0"
        assert registry_key in _PROMPT_REGISTRY
        assert _PROMPT_REGISTRY[registry_key]["name"] == "test.template"
        assert _PROMPT_REGISTRY[registry_key]["version"] == "1.0"

    def test_decorator_with_version(self) -> None:
        """Test that version parameter works."""

        @prompt_template(name="versioned.template", version="2.5.0")
        class VersionedTemplate:
            pass

        registry_key = "versioned.template@2.5.0"
        assert registry_key in _PROMPT_REGISTRY
        assert _PROMPT_REGISTRY[registry_key]["version"] == "2.5.0"

    def test_decorator_with_tags(self) -> None:
        """Test that tags parameter works."""

        @prompt_template(name="tagged.template", tags=["rag", "synthesis", "test"])
        class TaggedTemplate:
            pass

        registry_key = "tagged.template@1.0"
        assert registry_key in _PROMPT_REGISTRY
        assert _PROMPT_REGISTRY[registry_key]["tags"] == ["rag", "synthesis", "test"]

    def test_decorator_duplicate_raises(self) -> None:
        """Test that duplicate name@version raises error."""

        @prompt_template(name="duplicate.test", version="1.0")
        class FirstTemplate:
            pass

        with pytest.raises(ValueError, match="already registered"):
            @prompt_template(name="duplicate.test", version="1.0")
            class SecondTemplate:
                pass

    def test_decorator_preserves_function(self) -> None:
        """Test that original function still works."""

        @prompt_template(name="preserve.test")
        class PreservedTemplate:
            value = "original"

        assert PreservedTemplate.value == "original"
        assert hasattr(PreservedTemplate, "_prompt_name")
        assert PreservedTemplate._prompt_name == "preserve.test"
        assert hasattr(PreservedTemplate, "_prompt_version")
        assert PreservedTemplate._prompt_version == "1.0"

    def test_decorator_different_versions_coexist(self) -> None:
        """Test that same name with different versions can coexist."""

        @prompt_template(name="multi.version", version="1.0")
        class V1Template:
            pass

        @prompt_template(name="multi.version", version="2.0")
        class V2Template:
            pass

        assert "multi.version@1.0" in _PROMPT_REGISTRY
        assert "multi.version@2.0" in _PROMPT_REGISTRY
