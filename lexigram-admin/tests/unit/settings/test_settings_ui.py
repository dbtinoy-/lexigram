"""Tests for the spec-driven settings form rendering."""

from __future__ import annotations

from lexigram.admin.settings.panel.registry import ConfigRegistry
from lexigram.admin.settings.panel.ui import ConfigDashboardUI
from lexigram.ui import render_to_string


def _cache_spec_dict() -> dict:
    registry = ConfigRegistry.with_defaults()
    spec = registry.get_spec("admin.cache")
    assert spec is not None
    return {
        "namespace": spec.namespace,
        "label": spec.label,
        "description": spec.description,
        "nodes": [n.to_dict() for n in spec.get_nodes().values()],
    }


class TestBooleanFieldRendering:
    """Tests for boolean toggle field markup."""

    def test_boolean_field_renders_checkbox_with_true_value(self) -> None:
        form = render_to_string(
            ConfigDashboardUI().render_config_form(
                _cache_spec_dict(),
                values={},
                action="/admin/settings/admin.cache",
            )
        )
        assert 'type="checkbox" name="enabled"' in form
        assert 'value="true"' in form
        assert 'type="checkbox" name="default_ttl"' not in form

    def test_boolean_field_renders_hidden_false_input_after_checkbox(self) -> None:
        form = render_to_string(
            ConfigDashboardUI().render_config_form(
                _cache_spec_dict(),
                values={},
                action="/admin/settings/admin.cache",
            )
        )
        checkbox = form.index('type="checkbox" name="enabled"')
        hidden = form.index('type="hidden" name="enabled" value="false"')
        assert hidden > checkbox


class TestTypedFieldRendering:
    """Tests that typed nodes render the correct input widgets."""

    def test_color_node_renders_color_input(self) -> None:
        node = {
            "name": "primary_color",
            "label": "Primary",
            "type": "color",
            "default": "#6b7280",
            "help_text": None,
            "readonly": False,
            "options": [],
        }
        html = render_to_string(ConfigDashboardUI().render_field(node, {}))
        assert 'type="color" name="primary_color"' in html

    def test_secret_node_renders_password_input(self) -> None:
        node = {
            "name": "api_key",
            "label": "API Key",
            "type": "secret",
            "default": "sk-123",
            "help_text": None,
            "readonly": False,
            "options": [],
        }
        html = render_to_string(ConfigDashboardUI().render_field(node, {}))
        assert 'type="password" name="api_key"' in html
