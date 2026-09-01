"""Recoverable 200 form responses must not be announced as saved.

Settings validation and conflict fragments deliberately return ``200`` so
HTMX swaps the re-rendered form. The shared behavior layer therefore has to
inspect the payload rather than trusting ``detail.successful``, otherwise a
rejected save announces "Form saved." to assistive technology.
"""

from __future__ import annotations

from lexigram.admin.settings.panel.registry import ConfigRegistry
from lexigram.admin.settings.panel.ui import ConfigDashboardUI
from lexigram.admin.ui.templates.shell_scripts import admin_form_ux_script
from lexigram.ui import render_to_string


def _cache_spec_dict() -> dict:
    registry = ConfigRegistry.with_defaults()
    spec = registry.get_spec("admin.cache")
    assert spec is not None
    return spec.to_dict()


class TestFormBehaviorScript:
    def test_rejects_conflict_and_validation_status_codes(self) -> None:
        script = render_to_string(admin_form_ux_script())
        assert "xhr.status === 409" in script
        assert "xhr.status === 422" in script

    def test_inspects_payload_for_error_markers(self) -> None:
        script = render_to_string(admin_form_ux_script())
        assert "data-admin-form-error" in script
        assert 'aria-invalid="true"' in script

    def test_success_path_still_reports_saved(self) -> None:
        script = render_to_string(admin_form_ux_script())
        assert "'Form saved.'" in script
        assert "responseRejected(detail)" in script


class TestRenderedErrorMarkers:
    def test_field_error_marks_the_control_invalid(self) -> None:
        html = render_to_string(
            ConfigDashboardUI().render_config_form(
                spec=_cache_spec_dict(),
                values={"enabled": True, "default_ttl": 60},
                errors={"default_ttl": "must be positive"},
                action="/admin/settings/admin.cache",
                csrf_token="token",
            )
        )
        assert 'aria-invalid="true"' in html

    def test_form_level_error_carries_a_machine_readable_marker(self) -> None:
        html = render_to_string(
            ConfigDashboardUI().render_config_form(
                spec=_cache_spec_dict(),
                values={"enabled": True},
                errors={"__all__": "These settings changed in another session."},
                action="/admin/settings/admin.cache",
                csrf_token="token",
            )
        )
        assert 'data-admin-form-error="true"' in html

    def test_clean_form_has_no_error_markers(self) -> None:
        html = render_to_string(
            ConfigDashboardUI().render_config_form(
                spec=_cache_spec_dict(),
                values={"enabled": True, "default_ttl": 60},
                action="/admin/settings/admin.cache",
                csrf_token="token",
            )
        )
        assert 'data-admin-form-error="true"' not in html
        assert 'aria-invalid="true"' not in html

    def test_status_region_uses_the_shared_marker_contract(self) -> None:
        html = render_to_string(
            ConfigDashboardUI().render_config_form(
                spec=_cache_spec_dict(),
                values={"enabled": True, "default_ttl": 60},
                action="/admin/settings/admin.cache",
                csrf_token="token",
            )
        )
        assert 'data-admin-form-status="true"' in html
        assert 'data-admin-form-actions="true"' in html
