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
