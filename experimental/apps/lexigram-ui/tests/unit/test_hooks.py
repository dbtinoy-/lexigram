"""Tests for UI hooks and payloads."""

import pytest

from lexigram.ui.hooks import UIComponentRenderedHook, UITemplateRenderedHook


class TestUIComponentRenderedHook:
    """Tests for UIComponentRenderedHook."""

    def test_component_name_stored(self) -> None:
        """Test component name is stored in hook payload."""
        hook = UIComponentRenderedHook(component_name="UserCard")
        assert hook.component_name == "UserCard"

    def test_component_name_immutable(self) -> None:
        """Test component name cannot be modified after creation."""
        hook = UIComponentRenderedHook(component_name="UserCard")
        with pytest.raises(AttributeError):
            hook.component_name = "Different"

    def test_qualified_component_name(self) -> None:
        """Test fully qualified component name is preserved."""
        hook = UIComponentRenderedHook(
            component_name="lexigram.ui.molecules.card.UserCard"
        )
        assert hook.component_name == "lexigram.ui.molecules.card.UserCard"

    def test_dataclass_kw_only(self) -> None:
        """Test dataclass uses keyword-only fields."""
        with pytest.raises(TypeError):
            UIComponentRenderedHook("UserCard")

    def test_component_name_empty_string(self) -> None:
        """Test empty string component name is valid."""
        hook = UIComponentRenderedHook(component_name="")
        assert hook.component_name == ""

    def test_repr_includes_component_name(self) -> None:
        """Test repr includes component name."""
        hook = UIComponentRenderedHook(component_name="TestComponent")
        assert "TestComponent" in repr(hook)


class TestUITemplateRenderedHook:
    """Tests for UITemplateRenderedHook."""

    def test_template_name_stored(self) -> None:
        """Test template name is stored in hook payload."""
        hook = UITemplateRenderedHook(template_name="user_detail.html")
        assert hook.template_name == "user_detail.html"

    def test_template_name_immutable(self) -> None:
        """Test template name cannot be modified after creation."""
        hook = UITemplateRenderedHook(template_name="user_detail.html")
        with pytest.raises(AttributeError):
            hook.template_name = "other.html"

    def test_template_path(self) -> None:
        """Test template path is preserved."""
        hook = UITemplateRenderedHook(template_name="partials/user_card.html")
        assert hook.template_name == "partials/user_card.html"

    def test_dataclass_kw_only(self) -> None:
        """Test dataclass uses keyword-only fields."""
        with pytest.raises(TypeError):
            UITemplateRenderedHook("template.html")

    def test_template_name_empty_string(self) -> None:
        """Test empty string template name is valid."""
        hook = UITemplateRenderedHook(template_name="")
        assert hook.template_name == ""

    def test_repr_includes_template_name(self) -> None:
        """Test repr includes template name."""
        hook = UITemplateRenderedHook(template_name="test.html")
        assert "test.html" in repr(hook)


class TestHooksExport:
    """Tests for hooks module exports."""

    def test_ui_component_rendered_hook_exported(self) -> None:
        """Test UIComponentRenderedHook is exported."""
        from lexigram.ui.hooks import __all__

        assert "UIComponentRenderedHook" in __all__

    def test_ui_template_rendered_hook_exported(self) -> None:
        """Test UITemplateRenderedHook is exported."""
        from lexigram.ui.hooks import __all__

        assert "UITemplateRenderedHook" in __all__

    def test_all_contains_all_hooks(self) -> None:
        """Test __all__ contains all hook classes."""
        from lexigram.ui.hooks import __all__

        assert len(__all__) == 2