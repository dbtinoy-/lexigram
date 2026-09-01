"""Optimistic concurrency on settings writes must fail closed.

A submission that omits ``settings_revision`` used to skip the staleness
check entirely, so any client that dropped the field could overwrite a
newer save. These tests pin the fail-closed behaviour.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.controllers.settings import SettingsController
from lexigram.admin.settings.panel import CacheSpec
from lexigram.admin.settings.panel.registry import ConfigRegistry
from lexigram.admin.settings.revision import (
    extract_submitted_revision,
    revision_matches,
    settings_revision,
)


class _FakeUser:
    def __init__(self) -> None:
        self.permissions = frozenset({"admin.settings.edit"})
        self.roles: list[str] = []
        self.user_id = "user-1"
        self.username = "admin"


class _MultiForm:
    """FormData stand-in preserving duplicate field names."""

    def __init__(self, *items: tuple[str, str]) -> None:
        self._items = list(items)

    def multi_items(self) -> Any:
        return iter(self._items)


def _mock_request(form_data: dict[str, str], hx_request: bool = False) -> MagicMock:
    req = MagicMock(spec=Request)
    req.method = "POST"
    req.headers = {"hx-request": "true"} if hx_request else {}
    req.query_params = {}
    req.path_params = {"namespace": "admin.cache"}

    async def _form() -> dict[str, str]:
        return form_data

    req.form = _form
    req.state = MagicMock(user=_FakeUser())
    req.scope = {}
    return req


@pytest.fixture
def renderer() -> MagicMock:
    renderer = MagicMock()
    renderer.render_page = MagicMock(return_value=MagicMock(status_code=200))
    return renderer


class TestRevisionHelpers:
    def test_missing_revision_never_matches(self) -> None:
        assert revision_matches(None, CacheSpec, {"enabled": True}) is False
        assert revision_matches("", CacheSpec, {"enabled": True}) is False

    def test_matching_revision_matches(self) -> None:
        values = {"enabled": True, "default_ttl": 300}
        token = settings_revision(CacheSpec, values)
        assert revision_matches(token, CacheSpec, values) is True

    def test_changed_values_change_the_token(self) -> None:
        first = settings_revision(CacheSpec, {"enabled": True})
        second = settings_revision(CacheSpec, {"enabled": False})
        assert first != second

    def test_extract_reads_duplicate_preserving_forms(self) -> None:
        form = _MultiForm(("enabled", "true"), ("settings_revision", "abc"))
        assert extract_submitted_revision(form) == "abc"

    def test_extract_reads_plain_mappings(self) -> None:
        assert extract_submitted_revision({"settings_revision": "xyz"}) == "xyz"

    def test_extract_returns_none_when_absent_or_blank(self) -> None:
        assert extract_submitted_revision({}) is None
        assert extract_submitted_revision({"settings_revision": ""}) is None


class TestSaveSpecRequiresRevision:
    @pytest.mark.asyncio
    async def test_missing_revision_is_rejected_without_persisting(
        self, renderer: MagicMock
    ) -> None:
        registry = ConfigRegistry.with_defaults()
        await registry.save_values("admin.cache", {"default_ttl": "300"})
        audit = AsyncMock()
        controller = SettingsController(
            renderer=renderer, audit_service=audit, registry=registry
        )

        # No settings_revision field at all.
        req = _mock_request({"enabled": "true", "default_ttl": "999"})
        resp = await controller.save_spec(req)

        assert resp.status_code == 409
        values = await registry.get_values("admin.cache")
        assert values["default_ttl"] == 300

    @pytest.mark.asyncio
    async def test_missing_revision_is_audited_distinctly(
        self, renderer: MagicMock
    ) -> None:
        registry = ConfigRegistry.with_defaults()
        audit = AsyncMock()
        controller = SettingsController(
            renderer=renderer, audit_service=audit, registry=registry
        )

        await controller.save_spec(_mock_request({"default_ttl": "999"}))

        _, kwargs = audit.log_event.call_args
        assert kwargs["metadata"]["reason"] == "missing_settings_revision"

    @pytest.mark.asyncio
    async def test_stale_revision_is_audited_as_concurrent_update(
        self, renderer: MagicMock
    ) -> None:
        registry = ConfigRegistry.with_defaults()
        stale = settings_revision(CacheSpec, {"default_ttl": 1})
        audit = AsyncMock()
        controller = SettingsController(
            renderer=renderer, audit_service=audit, registry=registry
        )

        await controller.save_spec(
            _mock_request({"default_ttl": "999", "settings_revision": stale})
        )

        _, kwargs = audit.log_event.call_args
        assert kwargs["metadata"]["reason"] == "concurrent_update"

    @pytest.mark.asyncio
    async def test_current_revision_allows_the_write(self, renderer: MagicMock) -> None:
        registry = ConfigRegistry.with_defaults()
        current = await registry.get_values("admin.cache")
        token = settings_revision(CacheSpec, current)
        controller = SettingsController(renderer=renderer, registry=registry)

        resp = await controller.save_spec(
            _mock_request({"default_ttl": "999", "settings_revision": token})
        )

        assert resp.status_code == 302
        values = await registry.get_values("admin.cache")
        assert values["default_ttl"] == 999

    @pytest.mark.asyncio
    async def test_htmx_missing_revision_returns_recoverable_fragment(
        self, renderer: MagicMock
    ) -> None:
        registry = ConfigRegistry.with_defaults()
        controller = SettingsController(renderer=renderer, registry=registry)

        resp = await controller.save_spec(
            _mock_request({"default_ttl": "999"}, hx_request=True)
        )

        # HTMX swaps 200 responses; the fragment carries the conflict notice.
        assert resp.status_code == 200
        assert b"changed in another session" in resp.body
