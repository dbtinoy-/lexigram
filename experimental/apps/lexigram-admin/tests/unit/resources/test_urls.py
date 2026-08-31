"""Unit tests for admin URL helpers (configured-prefix resolution)."""

from __future__ import annotations

from types import SimpleNamespace

from lexigram.admin.resources.urls import (
    DEFAULT_ADMIN_PREFIX,
    admin_prefix_from_request,
    admin_url,
    mount_admin_url,
)


def _request(
    *,
    scope_prefix: str | None = None,
    app_state_prefix: str | None = None,
) -> SimpleNamespace:
    scope = {"admin_prefix": scope_prefix} if scope_prefix is not None else {}
    app = SimpleNamespace(state=SimpleNamespace())
    if app_state_prefix is not None:
        app.state.admin_prefix = app_state_prefix
    return SimpleNamespace(scope=scope, app=app)


def test_default_prefix_constant() -> None:
    assert DEFAULT_ADMIN_PREFIX == "/admin"


def test_prefix_resolved_from_scope() -> None:
    request = _request(scope_prefix="/backoffice")
    assert admin_prefix_from_request(request) == "/backoffice"


def test_prefix_resolved_from_app_state() -> None:
    request = _request(app_state_prefix="/console/")
    assert admin_prefix_from_request(request) == "/console"


def test_prefix_falls_back_to_default() -> None:
    assert admin_prefix_from_request(_request()) == "/admin"


def test_prefix_prefers_scope_over_app_state() -> None:
    request = _request(scope_prefix="/scope", app_state_prefix="/state")
    assert admin_prefix_from_request(request) == "/scope"


def test_prefix_ignores_non_string_scope_values() -> None:
    """MagicMock-based request helpers must not leak mock reprs into URLs."""
    from unittest.mock import MagicMock

    request = MagicMock()
    assert admin_prefix_from_request(request) == DEFAULT_ADMIN_PREFIX


def test_mount_admin_url_custom_prefix() -> None:
    assert mount_admin_url("/admin/login", "/console") == "/console/login"


def test_mount_admin_url_leaves_external_paths_untouched() -> None:
    assert mount_admin_url("/assets/admin.css", "/console") == "/assets/admin.css"


def test_admin_url_joins_part_and_suffix() -> None:
    assert admin_url("/admin", "users", "1/edit") == "/admin/users/1/edit"


def test_admin_url_custom_prefix() -> None:
    assert admin_url("/console", "users", "1/edit") == "/console/users/1/edit"


def test_admin_url_strips_duplicate_slashes() -> None:
    assert admin_url("/admin/", "users", "/1/edit") == "/admin/users/1/edit"


def test_admin_url_without_resource_name() -> None:
    assert admin_url("/admin", "", "settings") == "/admin/settings"


def test_admin_url_with_query() -> None:
    assert (
        admin_url("/admin", "users", query="notice=Saved.")
        == "/admin/users?notice=Saved."
    )


def test_admin_url_with_query_and_suffix() -> None:
    assert (
        admin_url("/admin", "users", "1/edit", query="tab=profile")
        == "/admin/users/1/edit?tab=profile"
    )
