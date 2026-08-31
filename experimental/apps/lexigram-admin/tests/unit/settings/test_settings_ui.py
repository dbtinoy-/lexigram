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

    def test_secret_node_never_leaks_the_stored_value(self) -> None:
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
        assert "sk-123" not in html
        assert "currently set" in html

    def test_secret_node_shows_not_set_when_no_value(self) -> None:
        node = {
            "name": "api_key",
            "label": "API Key",
            "type": "secret",
            "default": None,
            "help_text": None,
            "readonly": False,
            "options": [],
        }
        html = render_to_string(ConfigDashboardUI().render_field(node, {}))
        assert 'type="password" name="api_key"' in html
        assert "not set" in html


def test_numeric_constraints_and_settings_form_metadata_are_rendered() -> None:
    registry = ConfigRegistry.with_defaults()
    spec = registry.get_spec("admin.cache")
    assert spec is not None
    html = render_to_string(
        ConfigDashboardUI().render_config_form(
            spec.to_dict(),
            values={"enabled": True, "default_ttl": 60},
            action="/admin/settings/admin.cache",
        )
    )
    assert 'min="0"' in html
    assert 'data-settings-form="true"' in html
    assert html.count('type="submit"') == 1
    assert "Source: Database" in html


def test_csp_is_rendered_as_multiline_textarea() -> None:
    registry = ConfigRegistry.with_defaults()
    spec = registry.get_spec("admin.security")
    assert spec is not None
    html = render_to_string(
        ConfigDashboardUI().render_config_form(
            spec.to_dict(), values={}, action="/admin/settings/admin.security"
        )
    )
    assert "<textarea" in html
    assert 'name="csp"' in html


def test_legacy_main_content_delegates_to_shared_settings_form_contract() -> None:
    registry = ConfigRegistry.with_defaults()
    spec = registry.get_spec("admin.cache")
    assert spec is not None

    html = render_to_string(
        ConfigDashboardUI().render_main_content(
            spec.to_dict(),
            values={"enabled": True},
            namespace=spec.namespace,
            action="/console/settings/admin.cache",
            csrf_token="legacy-token",
        )
    )

    assert 'action="/console/settings/admin.cache"' in html
    assert 'data-admin-form="true"' in html
    assert 'data-settings-form="true"' in html
    assert 'name="csrf_token"' in html
    assert 'data-admin-form-status="true"' in html
    assert 'type="submit"' in html


def test_view_only_settings_render_disabled_fields_without_save_actions() -> None:
    registry = ConfigRegistry.with_defaults()
    spec = registry.get_spec("admin.cache")
    assert spec is not None
    spec_data = spec.to_dict()
    spec_data["can_edit"] = False

    html = render_to_string(
        ConfigDashboardUI().render_config_form(
            spec_data,
            values={"enabled": True, "default_ttl": 60},
            action="/admin/settings/admin.cache",
        )
    )

    assert "disabled" in html
    assert 'type="submit"' not in html
    assert "view-only access" in html
